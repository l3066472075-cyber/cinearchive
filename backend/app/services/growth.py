"""「搜索即喂养」自增长闭环。

每一次搜索/推荐请求、每一条反馈，都是资源库的增量原料：
1. log_search   —— 记录原始自述 + 意图标签 + 命中的影片；并给被用到的标签「升温」。
2. record_feedback —— 记录反馈；若用户建议了新标签，自动创建并挂到对应影片上。
3. compute_insights —— 聚合出「大家在找什么 / 未被满足的需求 / 待采纳标签」，
   供人工或 AI 策划者据此新增影片、补标签、写解读，让库不断迭代升级。
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from .. import models
from ..schemas import FeedbackResponse, Insight


def build_memory(db: Session, user: models.User | None) -> str:
    """构建用户的「过往记忆」（近期搜索 + 近期笔记要点），供 LLM 个性化回应。"""
    if user is None:
        return ""
    parts: list[str] = []
    searches = (
        db.query(models.SearchLog)
        .filter(models.SearchLog.user_id == user.id)
        .order_by(models.SearchLog.created_at.desc())
        .limit(5)
        .all()
    )
    queries = [s.raw_query for s in searches if s.raw_query]
    if queries:
        parts.append("近期搜索过：" + "、".join(queries))

    notes = (
        db.query(models.Note)
        .filter(models.Note.user_id == user.id)
        .order_by(models.Note.created_at.desc())
        .limit(3)
        .all()
    )
    for n in notes:
        vals = [str(v) for v in (n.content or {}).values() if v]
        if vals:
            parts.append(f"写过笔记：{' / '.join(vals)[:80]}")

    return "；".join(parts) if parts else ""


def log_search(
    db: Session,
    raw_query: str,
    intent_labels: list[str],
    matched_movie_ids: list[int],
    chosen_movie_id: int | None = None,
    source: str = "recommend",
    user_id: int | None = None,
) -> models.SearchLog:
    log = models.SearchLog(
        user_id=user_id,
        raw_query=raw_query,
        normalized_query=(raw_query or "").strip().lower(),
        intent_labels=intent_labels,
        matched_movie_ids=matched_movie_ids,
        chosen_movie_id=chosen_movie_id,
        source=source,
    )
    db.add(log)
    # 给被命中的意图标签「升温」，让高频情绪/境遇权重自然增长
    for name in intent_labels:
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if tag:
            tag.use_count = (tag.use_count or 0) + 1
    db.commit()
    db.refresh(log)
    return log


def _apply_suggested_tag(db: Session, movie_id: int, tag_name: str) -> bool:
    """把用户建议的标签落库并挂到影片上（自动增长标签体系）。"""
    name = (tag_name or "").strip()
    if not name:
        return False
    movie = db.get(models.Movie, movie_id)
    if movie is None:
        return False
    tag = db.query(models.Tag).filter(models.Tag.name == name).first()
    if tag is None:
        tag = models.Tag(
            name=name,
            category="emotion",  # 默认归入情感类，策划者可后续重分类
            description="由用户反馈建议新增的标签",
            source="user",
        )
        db.add(tag)
        db.flush()
    # 挂接（若已存在则加权）
    link = (
        db.query(models.MovieTag)
        .filter(models.MovieTag.movie_id == movie_id, models.MovieTag.tag_id == tag.id)
        .first()
    )
    if link:
        link.weight += 0.5
    else:
        db.add(models.MovieTag(movie_id=movie_id, tag_id=tag.id, weight=1.0, source="user"))
    return True


def record_feedback(db: Session, payload: dict) -> FeedbackResponse:
    fb = models.Feedback(
        user_id=payload.get("user_id"),
        search_log_id=payload.get("search_log_id"),
        movie_id=payload["movie_id"],
        helpful=payload.get("helpful"),
        rating=payload.get("rating"),
        comment=payload.get("comment", ""),
        suggested_tag=payload.get("suggested_tag", ""),
    )
    db.add(fb)
    applied: list[str] = []
    suggested = (payload.get("suggested_tag") or "").strip()
    if suggested:
        ok = _apply_suggested_tag(db, payload["movie_id"], suggested)
        if ok:
            fb.status = "applied"
            applied.append(suggested)
            # 失效推荐索引，让新标签进入下一次检索
            from ..ai import recommender

            recommender._index.invalidate()
    db.commit()
    db.refresh(fb)

    message = (
        f"感谢反馈！你建议的标签「{suggested}」已加入资源库，并关联到这部影片。"
        if applied
        else "感谢反馈，已记录，将帮助资源库更好地理解大家的需求。"
    )
    return FeedbackResponse(id=fb.id, status=fb.status, applied_tags=applied, message=message)


def compute_insights(db: Session) -> Insight:
    logs = db.query(models.SearchLog).all()

    query_counter: Counter[str] = Counter()
    emerging_counter: Counter[str] = Counter()
    for log in logs:
        q = (log.raw_query or "").strip()
        if not q:
            continue
        query_counter[q] += 1
        # 「未被满足」：没有任何影片命中，或推荐类请求未能理解其情绪/境遇
        if not log.matched_movie_ids or (log.source == "recommend" and not log.intent_labels):
            emerging_counter[q] += 1

    pending_suggestions = [
        f.suggested_tag
        for f in db.query(models.Feedback)
        .filter(models.Feedback.suggested_tag != "")
        .filter(models.Feedback.status == "new")
        .all()
    ]

    return Insight(
        top_queries=[{"query": q, "count": c} for q, c in query_counter.most_common(10)],
        emerging_needs=[{"query": q, "count": c} for q, c in emerging_counter.most_common(10)],
        pending_tag_suggestions=list(dict.fromkeys(pending_suggestions))[:20],
        total_searches=len(logs),
        total_movies=db.query(models.Movie).count(),
        total_tags=db.query(models.Tag).count(),
    )
