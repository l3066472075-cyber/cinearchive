"""反馈接口：用户反馈会转化为标签/档案的增量贡献。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..db import get_db
from ..schemas import FeedbackRequest, FeedbackResponse
from ..services import growth

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    payload = req.model_dump()
    payload["user_id"] = user.id if user else None
    return growth.record_feedback(db, payload)
