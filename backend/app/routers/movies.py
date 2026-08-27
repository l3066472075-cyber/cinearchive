"""影片档案接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..ai import llm
from ..db import get_db
from ..schemas import MovieBrief, MovieDetail, PersonalRequest, PersonalResponse
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


@router.post("/{movie_id}/personal", response_model=PersonalResponse)
def movie_personal(movie_id: int, req: PersonalRequest, db: Session = Depends(get_db)):
    """按用户的 5 问答案，生成亲切的「这部影片如何支持你」+「观影观己」讨论问题。"""
    # 用 library 拿完整详情（含 synopsis/therapy_notes/discussion_questions）
    detail = library.get_movie(db, movie_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="影片不存在")
    info = {
        "title": detail.title,
        "synopsis": detail.synopsis,
        "therapy_notes": detail.therapy_notes,
    }
    result = llm.personalize_movie(info, req.answers)
    if result is None:
        return PersonalResponse(
            support="这部影片如何支持你，留给你在观影中去体会。",
            questions=detail.discussion_questions or [],
        )
    return PersonalResponse(**result)
