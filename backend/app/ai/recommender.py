"""推荐引擎：把「情绪/境遇自述」翻译成电影推荐。

流程：query → 意图标签识别 → 语义向量匹配 → 标签加权 → 质量重排 → 生成解释。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .. import models
from ..schemas import RecommendItem, MovieDetail
from . import embeddings, llm

# —— 情感/境遇 同义词词典（把大白话映射到规范标签）——
SYNONYMS: dict[str, list[str]] = {
    "无力感": ["无力", "无助", "使不上劲", "精疲力尽", "耗尽", "撑不下去", "没劲", "累了"],
    "亲子冲突": ["亲子", "交流不顺", "沟通不畅", "叛逆", "不听话", "代沟", "管不住", "跟孩子"],
    "青春期": ["青春期", "叛逆期", "少年", "青少年", "十几岁"],
    "丧失与哀伤": ["丧失", "失去", "离世", "去世", "死亡", "哀伤", "悲伤", "丧亲", "永别", "悼念", "走了"],
    "职业倦怠": ["倦怠", "工作", "职业", "加班", "内耗", "职场", "辞", "压力大"],
    "孤独": ["孤独", "寂寞", "没人理解", "被孤立", "一个人"],
    "焦虑": ["焦虑", "紧张", "不安", "压力", "担心", "恐慌", "心慌"],
    "迷茫": ["迷茫", "找不到方向", "困惑", "迷失", "不知道怎么办", "人生意义", "路在何方"],
    "自我认同": ["自我", "认同", "我是谁", "自卑", "不自信", "接纳自己", "价值感"],
    "希望": ["希望", "绝望", "放弃", "坚持不下去", "没信心", "灰心"],
    "家庭关系": ["家庭", "父母", "父子", "母女", "家人", "原生家庭", "爸妈"],
    "抑郁": ["抑郁", "低落", "情绪不好", "开心不起来", "兴趣", "想哭"],
    # 正向情绪
    "兴奋": ["兴奋", "激动", "热血", "燃", "太爽", "停不下来", "high"],
    "喜悦": ["喜悦", "开心", "高兴", "快乐", "愉悦", "欢喜"],
    "感动": ["感动", "泪目", "想哭", "被戳中", "暖到", "戳中"],
    "惊叹": ["惊叹", "震撼", "惊艳", "叹为观止", "太牛", "哇塞"],
    "满足": ["满足", "充实", "踏实", "圆满", "心安"],
    "平静": ["平静", "安宁", "松弛", "放松", "静心", "心静"],
    "期待": ["期待", "盼望", "憧憬", "向往", "跃跃欲试"],
    "温暖": ["温暖", "暖心", "温馨", "被爱", "治愈"],
    "振奋": ["振奋", "鼓舞", "来劲", "元气满满", "满血"],
}


def extract_intent_from_query(query: str, tag_names: list[str]) -> list[str]:
    """从自述中识别情感/境遇标签（纯函数，供 LangGraph 节点与搜索复用）。"""
    q = query or ""
    labels: list[str] = []
    # 1) 直接匹配库内标签名
    for name in tag_names:
        if name and name in q:
            labels.append(name)
    # 2) 同义词匹配（大白话 → 规范标签）
    for canonical, kws in SYNONYMS.items():
        if any(k in q for k in kws):
            labels.append(canonical)
    # 去重保序
    return list(dict.fromkeys(labels))


def extract_intent(query: str, db: Session) -> list[str]:
    """从自述中识别情感/境遇标签（从库内取标签名）。"""
    tag_names = [t.name for t in db.query(models.Tag).all()]
    return extract_intent_from_query(query, tag_names)


def build_movie_text(movie: models.Movie, tag_names: list[str]) -> str:
    """把影片档案拼接成用于嵌入的文本。"""
    da = movie.deep_analysis or {}
    parts = [
        movie.title,
        movie.title_en,
        movie.synopsis,
        " ".join(movie.genres or []),
        " ".join(movie.cast or []),
        movie.director,
        da.get("theme", ""),
        da.get("art_value", ""),
        da.get("edu_value", ""),
        da.get("therapy_value", ""),
        " ".join(movie.support_audiences or []),
        " ".join(movie.support_types or []),
        " ".join(tag_names),
    ]
    return " ".join(p for p in parts if p)


@dataclass
class MovieIndex:
    """影片向量索引（懒加载 + 可失效）。"""

    ids: list[int] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)
    text_map: dict[int, str] = field(default_factory=dict)
    _dirty: bool = True
    _count: int = 0

    def invalidate(self) -> None:
        self._dirty = True

    def ensure(self, db: Session) -> None:
        count = db.query(models.Movie).count()
        if not self._dirty and self._count == count and self.vectors:
            return
        self.ids = []
        self.vectors = []
        self.text_map = {}
        for movie in db.query(models.Movie).all():
            tag_names = [
                link.tag.name for link in movie.tags if link.tag is not None
            ]
            text = build_movie_text(movie, tag_names)
            self.ids.append(movie.id)
            self.vectors.append(embeddings.embed_text(text))
            self.text_map[movie.id] = text
        self._count = count
        self._dirty = False


_index = MovieIndex()


def _rating_score(movie: models.Movie) -> float:
    """把国内外评分归一化到 0-1（满分按 10 分制）。"""
    vals = [v for v in (movie.rating_domestic, movie.rating_international) if v and v > 0]
    if not vals:
        return 0.5
    return min(sum(vals) / len(vals) / 10.0, 1.0)


def recommend(
    db: Session,
    query: str,
    limit: int = 5,
    audience: str | None = None,
    with_explanation: bool = True,
) -> tuple[list[RecommendItem], list[str], str]:
    """返回 (推荐条目, 意图标签, 引擎标识)。"""
    intent = extract_intent(query, db)
    _index.ensure(db)

    # 查询向量 = 原始自述 + 规范化意图标签（把「交流不顺」等白话对齐到规范标签，
    # 从而能与影片档案中的标签名在向量空间命中）
    qvec = embeddings.embed_text(query + (" " + " ".join(intent) if intent else ""))
    scored: list[tuple[float, models.Movie, list[str], float, float, float]] = []

    for i, movie_id in enumerate(_index.ids):
        movie = db.get(models.Movie, movie_id)
        if movie is None:
            continue
        tag_names = [link.tag.name for link in movie.tags if link.tag is not None]
        sem = embeddings.cosine(qvec, _index.vectors[i])

        # 标签命中得分
        tag_score = 0.0
        matched: list[str] = []
        if intent:
            hits = [t for t in intent if t in tag_names]
            if hits:
                matched = hits
                tag_score = min(len(hits) / len(intent), 1.0)
        # 观众定向加成
        if audience:
            audience_hit = any(audience in a for a in (movie.support_audiences or []))
            tag_score = max(tag_score, 0.4) if audience_hit else tag_score * 0.5

        quality = _rating_score(movie)
        # 综合得分：有意图标签时，标签命中权重提升（意图驱动更精准）；
        # 否则以语义相似度为主。
        if intent:
            final = 0.45 * sem + 0.45 * tag_score + 0.1 * quality
        else:
            final = 0.7 * sem + 0.2 * tag_score + 0.1 * quality
        scored.append((final, movie, matched, sem, tag_score, quality))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    engine = "llm" if (with_explanation and llm.settings.llm_enabled) else "offline"
    items: list[RecommendItem] = []
    for final, movie, matched, _sem, _tag, _qual in top:
        explanation = ""
        if with_explanation:
            llm_text = llm.explain_recommendation(
                query, intent, movie.title, matched,
                movie.support_audiences or [], movie.therapy_notes or "",
            )
            explanation = llm_text or llm.template_explanation(
                query, movie.title, matched, movie.support_audiences or [],
            )
        items.append(
            RecommendItem(
                movie=MovieDetail.model_validate(_movie_to_dict(movie, db)),
                score=round(final, 4),
                matched_tags=matched,
                explanation=explanation,
            )
        )
    return items, intent, engine


def _movie_to_dict(movie: models.Movie, db: Session) -> dict:
    """把 ORM 影片对象转为 detail dict（含标签）。"""
    data = {c.name: getattr(movie, c.name) for c in models.Movie.__table__.columns}
    data["tags"] = [{"id": t.id, "name": t.name, "category": t.category,
                     "description": t.description or "", "use_count": t.use_count}
                    for t in (movie.tags and [l.tag for l in movie.tags if l.tag])]
    return data
