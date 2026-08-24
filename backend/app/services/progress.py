"""观心成长：段位 / 印记 / 打卡统计。

游戏化心法：用「心灯」的隐喻做段位，用「印记」替代奖杯，只呈现自己的成长，不做排行榜。
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .. import models

# 观心段位（score = 打卡天数 + 笔记数*2 + 搜索次数）
LEVELS = [
    {"name": "初见灯火", "desc": "你第一次推开了这座档案馆的门", "min": 0},
    {"name": "心有微光", "desc": "心里，有了一盏小小的灯", "min": 3},
    {"name": "心灯渐明", "desc": "灯一点点亮起来，开始照见自己", "min": 7},
    {"name": "照见自己", "desc": "电影成了你的一面镜子", "min": 14},
    {"name": "照亮他人", "desc": "你的光，开始温暖身边的人", "min": 21},
    {"name": "影领者", "desc": "以影为舟，领更多人渡河", "min": 30},
]

# 印记徽章（条件，名字，描述）
BADGES = [
    {"id": "first_search", "name": "初寻", "desc": "第一次为自己寻一部电影", "cond": lambda s: s["search_count"] >= 1},
    {"id": "first_light", "name": "灯初明", "desc": "点亮第一盏心灯", "cond": lambda s: s["checkin_days"] >= 1},
    {"id": "seven_days", "name": "七日心火", "desc": "累计七日观心打卡", "cond": lambda s: s["checkin_days"] >= 7},
    {"id": "twentyone", "name": "廿一日明", "desc": "二十一日，心灯长明", "cond": lambda s: s["checkin_days"] >= 21},
    {"id": "first_note", "name": "观心一记", "desc": "写下第一篇观电影法笔记", "cond": lambda s: s["note_count"] >= 1},
    {"id": "three_notes", "name": "三回照见", "desc": "三篇笔记，三回照见自己", "cond": lambda s: s["note_count"] >= 3},
]


def _score(checkin_days: int, note_count: int, search_count: int) -> int:
    return checkin_days + note_count * 2 + search_count


def _level_index(score: int) -> int:
    idx = 0
    for i, lv in enumerate(LEVELS):
        if score >= lv["min"]:
            idx = i
    return idx


def _streak(dates: list[date]) -> int:
    """当前连续打卡天数（从今天往前数）。"""
    ds = set(dates)
    today = date.today()
    if today not in ds:
        today = today - timedelta(days=1)  # 今天还没打，从昨天起算
    n = 0
    while today in ds:
        n += 1
        today -= timedelta(days=1)
    return n


def compute_progress(db: Session, user: models.User) -> dict:
    checkins = (
        db.query(models.CheckIn).filter(models.CheckIn.user_id == user.id).all()
    )
    checkin_days = len(checkins)
    checkin_dates = [date.fromisoformat(c.date) for c in checkins if c.date]
    note_count = db.query(models.Note).filter(models.Note.user_id == user.id).count()
    search_count = db.query(models.SearchLog).filter(models.SearchLog.user_id == user.id).count()

    score = _score(checkin_days, note_count, search_count)
    idx = _level_index(score)
    level = LEVELS[idx]
    next_level = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None

    if next_level:
        span = next_level["min"] - level["min"]
        pct = int((score - level["min"]) / span * 100) if span else 100
    else:
        pct = 100

    stats = {"checkin_days": checkin_days, "note_count": note_count, "search_count": search_count}
    badges = [
        {"id": b["id"], "name": b["name"], "desc": b["desc"], "earned": bool(b["cond"](stats))}
        for b in BADGES
    ]

    return {
        "level": idx,
        "level_name": level["name"],
        "level_desc": level["desc"],
        "next_level_name": next_level["name"] if next_level else "已达最高段位",
        "progress_pct": max(0, min(100, pct)),
        "badges": badges,
        "checkin_days": checkin_days,
        "checkin_streak": _streak(checkin_dates),
        "search_count": search_count,
        "note_count": note_count,
        "city": user.city or "",
    }
