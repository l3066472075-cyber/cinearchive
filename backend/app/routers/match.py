"""同频影友匹配：按城市坐标 + 近期心境标签，找到「同频的人」。

只返回聚合统计，不暴露他人隐私。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..db import get_db
from ..schemas import MatchResponse

router = APIRouter(prefix="/api/v1", tags=["match"])


@router.get("/match", response_model=MatchResponse)
def match(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """返回：同城影友数 + 与近期心境共振的影友标签。"""
    same_city_count = 0
    if user.city:
        same_city_count = (
            db.query(models.User)
            .filter(models.User.city == user.city, models.User.id != user.id)
            .count()
        )

    # 我近期的心境标签
    recent = (
        db.query(models.SearchLog)
        .filter(models.SearchLog.user_id == user.id)
        .order_by(models.SearchLog.created_at.desc())
        .limit(10)
        .all()
    )
    my_tags: list[str] = []
    for r in recent:
        for t in r.intent_labels or []:
            if t and t not in my_tags:
                my_tags.append(t)
    my_tags = my_tags[:5]

    # 他人近期也在找这些标签的人数（共鸣）
    others = (
        db.query(models.SearchLog)
        .filter(models.SearchLog.user_id != user.id)
        .all()
    )
    resonance = []
    for tag in my_tags:
        cnt = sum(1 for r in others if tag in (r.intent_labels or []))
        if cnt:
            resonance.append({"tag": tag, "count": cnt})
    resonance.sort(key=lambda x: -x["count"])

    return MatchResponse(
        city=user.city or "",
        same_city_count=same_city_count,
        my_tags=my_tags,
        resonance=resonance[:5],
    )
