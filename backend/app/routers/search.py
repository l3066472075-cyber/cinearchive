"""搜索接口（同样会写入搜索日志，喂养资源库）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..ai import recommender
from ..db import get_db
from ..schemas import SearchRequest, SearchResponse
from ..services import growth, library

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(
    req: SearchRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    items = library.search_movies(
        db, q=req.q, theme=req.theme, audience=req.audience,
        min_rating=req.min_rating, limit=req.limit,
    )
    matched_ids = [it.id for it in items]
    intent = recommender.extract_intent(req.q, db)
    log = growth.log_search(
        db,
        raw_query=req.q,
        intent_labels=intent,
        matched_movie_ids=matched_ids,
        chosen_movie_id=matched_ids[0] if matched_ids else None,
        source="search",
        user_id=user.id if user else None,
    )
    return SearchResponse(
        q=req.q, items=items, total=len(items), search_log_id=log.id
    )
