"""标签、统计与健康检查接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db
from ..schemas import HealthResponse, Insight, TagOut
from ..services import growth

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/tags", response_model=list[TagOut])
def list_tags(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Tag)
    if category:
        q = q.filter(models.Tag.category == category)
    return q.order_by(models.Tag.use_count.desc(), models.Tag.name).all()


@router.get("/themes", response_model=dict[str, list[TagOut]])
def list_themes(db: Session = Depends(get_db)):
    """按分类组织标签，便于前端构建筛选与导航。"""
    out: dict[str, list[TagOut]] = {}
    for tag in db.query(models.Tag).order_by(models.Tag.use_count.desc()).all():
        out.setdefault(tag.category, []).append(
            TagOut.model_validate(tag)
        )
    return out


@router.get("/insights", response_model=Insight)
def insights(db: Session = Depends(get_db)):
    return growth.compute_insights(db)


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        llm_enabled=settings.llm_enabled,
        embedding_enabled=settings.embedding_enabled,
        wx_enabled=settings.wx_enabled,
        movies=db.query(models.Movie).count(),
        tags=db.query(models.Tag).count(),
        searches=db.query(models.SearchLog).count(),
    )
