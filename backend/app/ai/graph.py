"""LangGraph 推荐状态图：把「情绪/境遇自述」翻译成电影推荐。

状态图节点（有向无环）：
  START → recognize_intent → retrieve → rerank → explain → END

- recognize_intent  意图识别（词典 + 同义词映射，纯函数）
- retrieve          语义召回（LangChain 嵌入，离线哈希回退）
- rerank            标签加权 + 质量/观众定向重排
- explain           生成推荐理由（LangChain ChatOpenAI，模板回退）

LangGraph 让推荐流程的每一步都成为可观测、可扩展、可替换的节点。
"""
from __future__ import annotations

import concurrent.futures
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..schemas import MovieDetail, RecommendItem
from . import embeddings, llm, recommender


class RecState(TypedDict):
    query: str
    audience: str | None
    limit: int
    with_explanation: bool
    tag_names: list[str]
    index_ids: list[int]
    index_vectors: list[list[float]]
    movies: dict  # movie_id -> {detail, tag_names, support_audiences, quality}
    intent_labels: list[str]
    retrieved: list[dict]
    candidates: list[dict]
    engine: str


# ---------------- 节点 ----------------
def recognize_intent(state: RecState) -> dict:
    intent = recommender.extract_intent_from_query(state["query"], state["tag_names"])
    return {"intent_labels": intent}


def retrieve(state: RecState) -> dict:
    intent = state["intent_labels"]
    qtext = state["query"] + ((" " + " ".join(intent)) if intent else "")
    qvec = embeddings.embed_text(qtext)
    scored = []
    for i, mid in enumerate(state["index_ids"]):
        sem = embeddings.cosine(qvec, state["index_vectors"][i])
        scored.append({"movie_id": mid, "sem": sem})
    scored.sort(key=lambda x: x["sem"], reverse=True)
    return {"retrieved": scored}


def rerank(state: RecState) -> dict:
    intent = state["intent_labels"]
    audience = state.get("audience")
    out = []
    for r in state["retrieved"]:
        entry = state["movies"][r["movie_id"]]
        tag_names = entry["tag_names"]
        matched = [t for t in intent if t in tag_names]
        tag_score = (len(matched) / len(intent)) if intent else 0.0
        if audience:
            hit = any(audience in a for a in (entry["support_audiences"] or []))
            tag_score = max(tag_score, 0.4) if hit else tag_score * 0.5
        quality = entry["quality"]
        sem = r["sem"]
        final = (
            (0.45 * sem + 0.45 * tag_score + 0.1 * quality)
            if intent
            else (0.7 * sem + 0.2 * tag_score + 0.1 * quality)
        )
        out.append(
            {"movie_id": r["movie_id"], "score": final, "matched_tags": matched}
        )
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"candidates": out[: state["limit"]]}


def explain(state: RecState) -> dict:
    use_llm = bool(state["with_explanation"] and settings.llm_enabled)
    cands = state["candidates"]

    # 优先「一次调用批量生成」前 3 部推荐理由（最快；DeepSeek 并发限流时串行/并行都很慢；
    # 只解释前 3 部可让批量 token 减半，第 4~5 部走模板兜底）
    batch: dict[str, str] = {}
    if use_llm and len(cands) > 1:
        movies_info = [
            {
                "title": state["movies"][c["movie_id"]]["detail"]["title"],
                "matched_tags": c["matched_tags"],
                "support_audiences": state["movies"][c["movie_id"]]["support_audiences"] or [],
                "therapy_notes": state["movies"][c["movie_id"]].get("therapy_notes", ""),
            }
            for c in cands[:3]
        ]
        batch = llm.explain_movies_batch(state["query"], state["intent_labels"], movies_info) or {}

    def gen(c: dict) -> dict:
        entry = state["movies"][c["movie_id"]]
        detail = entry["detail"]
        explanation = batch.get(detail["title"], "")
        if not explanation and state["with_explanation"]:
            # 仅当批量完全失败时才逐个调单条 LLM；批量成功则第 4~5 条直接用模板
            if use_llm and not batch:
                explanation = llm.explain_recommendation(
                    state["query"],
                    state["intent_labels"],
                    detail["title"],
                    c["matched_tags"],
                    entry["support_audiences"] or [],
                    entry.get("therapy_notes", ""),
                ) or ""
            if not explanation:
                explanation = llm.template_explanation(
                    state["query"],
                    detail["title"],
                    c["matched_tags"],
                    entry["support_audiences"] or [],
                )
        return {**c, "explanation": explanation}

    # 兜底：批量失败时并行生成（httpx.Client 线程安全）
    if use_llm and not batch and len(cands) > 1:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(cands), 5)
        ) as ex:
            candidates = list(ex.map(gen, cands))
    else:
        candidates = [gen(c) for c in cands]
    return {"candidates": candidates, "engine": "llm" if use_llm else "offline"}


# ---------------- 构建图 ----------------
_graph: StateGraph | None = None


def build_graph():
    global _graph
    if _graph is None:
        g = StateGraph(RecState)
        g.add_node("recognize_intent", recognize_intent)
        g.add_node("retrieve", retrieve)
        g.add_node("rerank", rerank)
        g.add_node("explain", explain)
        g.add_edge(START, "recognize_intent")
        g.add_edge("recognize_intent", "retrieve")
        g.add_edge("retrieve", "rerank")
        g.add_edge("rerank", "explain")
        g.add_edge("explain", END)
        _graph = g.compile()
    return _graph


# ---------------- 对外入口 ----------------
def recommend(
    db: Session,
    query: str,
    limit: int = 5,
    audience: str | None = None,
    with_explanation: bool = True,
) -> tuple[list[RecommendItem], list[str], str]:
    """返回 (推荐条目, 意图标签, 引擎标识)。"""
    recommender._index.ensure(db)

    tag_names = [t.name for t in db.query(models.Tag).all()]
    movies: dict = {}
    for mid in recommender._index.ids:
        movie = db.get(models.Movie, mid)
        if movie is None:
            continue
        movies[mid] = {
            "detail": recommender._movie_to_dict(movie, db),
            "tag_names": [link.tag.name for link in movie.tags if link.tag is not None],
            "support_audiences": movie.support_audiences or [],
            "therapy_notes": movie.therapy_notes or "",
            "quality": recommender._rating_score(movie),
        }

    state: RecState = {
        "query": query,
        "audience": audience,
        "limit": limit,
        "with_explanation": with_explanation,
        "tag_names": tag_names,
        "index_ids": recommender._index.ids,
        "index_vectors": recommender._index.vectors,
        "movies": movies,
        "intent_labels": [],
        "retrieved": [],
        "candidates": [],
        "engine": "offline",
    }

    result = build_graph().invoke(state)

    items: list[RecommendItem] = []
    for c in result["candidates"]:
        entry = movies[c["movie_id"]]
        items.append(
            RecommendItem(
                movie=MovieDetail.model_validate(entry["detail"]),
                score=round(c["score"], 4),
                matched_tags=c["matched_tags"],
                explanation=c.get("explanation", ""),
            )
        )
    return items, result["intent_labels"], result["engine"]
