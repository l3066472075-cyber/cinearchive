"""推荐接口：输入情绪/境遇自述，返回电影 + 理由。同时写入搜索日志（喂养库）。

推荐流程由 LangGraph 状态图驱动（app/ai/graph.py）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..ai import graph, llm
from ..config import settings
from ..db import get_db
from ..schemas import GuidedRequest, GuidedResponse, RecommendRequest, RecommendResponse
from ..services import growth

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    items, intent, engine = graph.recommend(
        db, req.query, limit=req.limit, audience=req.audience,
        with_explanation=req.with_explanation,
    )
    matched_ids = [it.movie.id for it in items]
    log = growth.log_search(
        db,
        raw_query=req.query,
        intent_labels=intent,
        matched_movie_ids=matched_ids,
        chosen_movie_id=matched_ids[0] if matched_ids else None,
        source="recommend",
        user_id=user.id if user else None,
    )
    return RecommendResponse(
        query=req.query,
        intent_labels=intent,
        items=items,
        engine=engine,
        search_log_id=log.id,
        note=(
            "已记录本次搜索，成为资源库的迭代原料。"
            "（配置 LLM_API_KEY / LLM_BASE_URL 后可启用大模型生成更个性化的推荐理由）"
            if engine == "offline"
            else ""
        ),
    )


@router.post("/recommend/guided", response_model=GuidedResponse)
def guided_recommend(
    req: GuidedRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """双角色 · 5 问引导推荐：把 5 个维度的答案合成，推荐电影并生成角色化解读。"""
    tags = [v for v in req.answers.values() if v]
    query = " ".join(tags)

    items, intent, _engine = graph.recommend(
        db, query, limit=req.limit,
        audience=req.answers.get("audience"),
        with_explanation=True,
    )
    matched_ids = [it.movie.id for it in items]
    log = growth.log_search(
        db,
        raw_query=query,
        intent_labels=intent,
        matched_movie_ids=matched_ids,
        chosen_movie_id=matched_ids[0] if matched_ids else None,
        source="recommend",
        user_id=user.id if user else None,
    )

    # 把候选影片的真实简介/治疗要点传给 LLM，避免编造剧情
    movie_infos = [
        {
            "title": it.movie.title,
            "synopsis": it.movie.synopsis,
            "therapy_notes": it.movie.therapy_notes,
        }
        for it in items
    ]
    titles = [it.movie.title for it in items]
    interpretation = llm.guided_interpretation(
        req.role, req.answers, movie_infos
    ) or llm.template_guided_interpretation(req.role, req.answers, titles)

    return GuidedResponse(
        role=req.role,
        intent_labels=intent,
        items=items,
        interpretation=interpretation,
        engine="llm" if settings.llm_enabled else "offline",
        search_log_id=log.id,
    )
