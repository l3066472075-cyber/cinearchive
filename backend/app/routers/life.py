"""「你的人生电影」接口：把人生档案 / 当天剧情，用电影视角生成回应。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..ai import llm
from ..db import get_db
from ..schemas import (
    LifeChatRequest,
    LifeChatResponse,
    LifeDailyRequest,
    LifeDailyResponse,
    LifeMovieRequest,
    LifeMovieResponse,
)

router = APIRouter(prefix="/api/v1/life", tags=["life"])


@router.post("/movie", response_model=LifeMovieResponse)
def life_movie(req: LifeMovieRequest):
    """按角色档案生成「你的人生电影」（片名/类型/海报文案/影评）。"""
    result = llm.life_movie(req.profile)
    if result is None:
        role_name = req.profile.get("role_name") or "你"
        return LifeMovieResponse(
            title=req.profile.get("movie_name") or f"{role_name}的人生电影",
            genre="人生电影",
            tagline="人生如戏，观影观己。",
            review="你的人生这部电影，正在上映。把目光从别人的银幕收回来，看看自己走过的路——那里面，有一个值得被看见、被欣赏的你。",
        )
    return LifeMovieResponse(**result)


@router.post("/chat", response_model=LifeChatResponse)
def life_chat(req: LifeChatRequest):
    """人生电影 · 对话模式：用户写下感受与想法，AI 进一步互动并可抛出觉察问题。"""
    reply = llm.life_chat(req.profile, req.history, req.message)
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
