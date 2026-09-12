"""「你的人生电影」接口：把人生档案 / 当天剧情，用电影视角生成回应，并留下个人档案。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..ai import llm
from ..db import get_db
from ..schemas import (
    LifeChatRequest,
    LifeChatResponse,
    LifeDailyRequest,
    LifeDailyResponse,
    LifeLogItem,
    LifeMovieRequest,
    LifeMovieResponse,
)

router = APIRouter(prefix="/api/v1/life", tags=["life"])


def _life_memory(db: Session, user: models.User | None) -> str:
    """把用户过去几次「看见的那条线」压成一句话，供大模型对照（成本极低）。"""
    if user is None:
        return ""
    logs = (
        db.query(models.LifeLog)
        .filter(models.LifeLog.user_id == user.id)
        .order_by(models.LifeLog.created_at.desc())
        .limit(3)
        .all()
    )
    items = []
    for lg in logs:
        if not lg.title:
            continue
        when = lg.created_at.strftime("%Y-%m") if lg.created_at else ""
        pat = (lg.pattern or "").strip()
        items.append(f"《{lg.title}》{('（' + when + '）') if when else ''}{('：' + pat) if pat else ''}")
    return "；".join(items)


@router.post("/movie", response_model=LifeMovieResponse)
def life_movie(
    req: LifeMovieRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """按角色档案生成「你的人生电影」，并自动存入「我的观心」档案。"""
    memory = _life_memory(db, user)
    result = llm.life_movie(req.profile, req.context, memory=memory)
    if result is None:
        role_name = req.profile.get("role_name") or "你"
        return LifeMovieResponse(
            title=req.profile.get("movie_name") or f"{role_name}的人生电影",
            genre="人生电影",
            tagline="人生如戏，观影观己。",
            review="你的人生这部电影，正在上映。把目光从别人的银幕收回来，看看自己走过的路——那里面，有一个值得被看见、被欣赏的你。",
            pattern="",
        )

    log_id = None
    if user is not None:
        log = models.LifeLog(
            user_id=user.id,
            profile=req.profile or {},
            title=str(result.get("title") or "")[:120],
            genre=str(result.get("genre") or "")[:80],
            tagline=str(result.get("tagline") or "")[:200],
            review=str(result.get("review") or ""),
            pattern=str(result.get("pattern") or "")[:200],
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id

    return LifeMovieResponse(id=log_id, **result)


@router.get("/logs", response_model=list[LifeLogItem])
def list_life_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """我的人生电影片单（按时间倒序）。"""
    if user is None:
        return []
    logs = (
        db.query(models.LifeLog)
        .filter(models.LifeLog.user_id == user.id)
        .order_by(models.LifeLog.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [
        LifeLogItem(
            id=lg.id,
            profile=lg.profile or {},
            title=lg.title or "",
            genre=lg.genre or "",
            tagline=lg.tagline or "",
            review=lg.review or "",
            pattern=lg.pattern or "",
            created_at=lg.created_at,
        )
        for lg in logs
    ]


@router.post("/chat", response_model=LifeChatResponse)
def life_chat(
    req: LifeChatRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """人生电影 · 对话模式：用户写下感受与想法，AI 进一步互动并可抛出觉察问题。"""
    reply = llm.life_chat(req.profile, req.history, req.message, req.context)
    if reply is None:
        return LifeChatResponse(reply="我在。慢慢说，我陪着你——你此刻想到的，往往正是最值得看一眼的那一处。")
    return LifeChatResponse(reply=reply)


@router.post("/daily", response_model=LifeDailyResponse)
def life_daily(req: LifeDailyRequest):
    """针对当天的一段「剧情」复盘回应（电影视角）。"""
    result = llm.life_daily(req.story, req.name)
    if result is None:
        return LifeDailyResponse(
            title="今日这一幕",
            review="谢谢你记下今天的这一段。它也许很平凡，却是你人生电影里真实的一帧——被记录的这一刻，就已经值得被看见。",
        )
    return LifeDailyResponse(**result)
