"""观心成长接口：段位/印记进度、21天打卡点灯、城市坐标。"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..db import get_db
from ..schemas import CheckInRequest, CheckInResponse, CityUpdate, ProgressResponse
from ..services import progress as progress_svc

router = APIRouter(prefix="/api/v1", tags=["growth"])


@router.get("/me/progress", response_model=ProgressResponse)
def get_progress(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """我的观心成长进度（需登录）。"""
    return progress_svc.compute_progress(db, user)


@router.post("/checkin", response_model=CheckInResponse)
def checkin(
    req: CheckInRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """21天观电影法打卡：点亮今天的心灯。"""
    today = req.date or datetime.now().strftime("%Y-%m-%d")
    existing = (
        db.query(models.CheckIn)
        .filter(models.CheckIn.user_id == user.id, models.CheckIn.date == today)
        .first()
    )
    if existing:
        if req.note and not existing.note:
            existing.note = req.note
            db.commit()
        lit = (
            db.query(models.CheckIn)
            .filter(models.CheckIn.user_id == user.id)
            .count()
        )
        return CheckInResponse(ok=True, date=today, lit_days=lit, message="今天的心灯已经点亮了，明天再来。")

    db.add(
        models.CheckIn(
            user_id=user.id, date=today, movie_id=req.movie_id, note=req.note
        )
    )
    db.commit()
    lit = (
        db.query(models.CheckIn).filter(models.CheckIn.user_id == user.id).count()
    )
    return CheckInResponse(ok=True, date=today, lit_days=lit, message=f"第 {lit} 盏心灯，为你点亮。🌙")


@router.patch("/me/city", response_model=ProgressResponse)
def update_city(
    req: CityUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """更新城市坐标（用于找同城影友）。"""
    user.city = req.city.strip()
    db.commit()
    return progress_svc.compute_progress(db, user)


# 观心月历关键词（按心境映射一个「观心字」）+ 《观电影法》原话
KEYWORD_MAP = {
    "无力感": "蓄力", "焦虑": "松绑", "迷茫": "照见", "悲伤": "渡", "丧失与哀伤": "渡",
    "兴奋": "光亮", "喜悦": "光亮", "感动": "暖", "平静": "定", "希望": "光",
    "自我认同": "立", "和解": "和", "孤独": "伴", "抑郁": "慢",
}
BOOK_QUOTES = ["生命是条长河，最终渡你的还是自己"]


@router.get("/me/monthly")
def monthly_report(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """观心月历：本月，你的心境与电影。"""
    month_start = date.today().replace(day=1).strftime("%Y-%m-%d")

    checkins = (
        db.query(models.CheckIn)
        .filter(models.CheckIn.user_id == user.id, models.CheckIn.date >= month_start)
        .count()
    )
    searches = (
        db.query(models.SearchLog)
        .filter(models.SearchLog.user_id == user.id)
        .all()
    )
    # 本月搜索（按 created_at 粗算）
    from datetime import datetime as dt

    month_dt = dt.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    search_month = sum(1 for s in searches if s.created_at and s.created_at >= month_dt)
    notes = (
        db.query(models.Note)
        .filter(models.Note.user_id == user.id)
        .all()
    )
    note_month = sum(1 for n in notes if n.created_at and n.created_at >= month_dt)

    # 本月心境标签（从搜索日志取）
    tag_counter: dict[str, int] = {}
    for s in searches:
        if s.created_at and s.created_at >= month_dt:
            for t in s.intent_labels or []:
                tag_counter[t] = tag_counter.get(t, 0) + 1
    top_tag = max(tag_counter, key=tag_counter.get) if tag_counter else ""
    keyword = KEYWORD_MAP.get(top_tag, "观")

    return {
        "month": date.today().strftime("%Y-%m"),
        "search_month": search_month,
        "checkin_month": checkins,
        "note_month": note_month,
        "top_tag": top_tag,
        "keyword": keyword,
        "quote": BOOK_QUOTES[0],
        "level_name": progress_svc.compute_progress(db, user)["level_name"],
    }
