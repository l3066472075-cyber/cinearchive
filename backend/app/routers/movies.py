"""影片档案接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import MovieBrief, MovieDetail
from ..services import library

router = APIRouter(prefix="/api/v1/movies", tags=["movies"])


@router.get("", response_model=list[MovieBrief])
def list_movies(
    theme: str | None = Query(None, description="按主题标签筛选"),
    audience: str | None = Query(None, description="按支持人群筛选"),
    min_rating: float | None = Query(None, ge=0, le=10),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return library.list_movies(db, theme=theme, audience=audience, min_rating=min_rating, limit=limit)


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = library.get_movie(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="影片不存在")
    return movie
