"""影片档案的查询与搜索服务。"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models
from ..ai import embeddings, recommender
from ..schemas import MovieBrief, MovieDetail


def _movie_dict(movie: models.Movie) -> dict:
    return {c.name: getattr(movie, c.name) for c in models.Movie.__table__.columns}


def _to_detail(movie: models.Movie) -> MovieDetail:
    data = _movie_dict(movie)
    data["tags"] = [
        {
            "id": link.tag.id,
            "name": link.tag.name,
            "category": link.tag.category,
            "description": link.tag.description or "",
            "use_count": link.tag.use_count,
        }
        for link in movie.tags
        if link.tag is not None
    ]
    return MovieDetail.model_validate(data)


def _to_brief(movie: models.Movie) -> MovieBrief:
    return MovieBrief.model_validate(_movie_dict(movie))


def get_movie(db: Session, movie_id: int) -> MovieDetail | None:
    movie = db.get(models.Movie, movie_id)
    return _to_detail(movie) if movie else None


def _keyword_score(movie: models.Movie, q: str) -> float:
    """关键字命中分（title/synopsis/director/cast）。"""
    ql = q.lower()
    hay = " ".join([
        movie.title, movie.title_en, movie.director,
        movie.synopsis, " ".join(movie.cast or []),
    ]).lower()
    if ql in hay:
        return 1.0
    # 部分词命中
    terms = [t for t in ql.replace("，", " ").replace(",", " ").split() if len(t) > 1]
    if not terms:
        return 0.0
    hits = sum(1 for t in terms if t in hay)
    return hits / len(terms)


def list_movies(
    db: Session,
    theme: str | None = None,
    audience: str | None = None,
    min_rating: float | None = None,
    limit: int = 20,
) -> list[MovieBrief]:
    query = db.query(models.Movie)
    if theme:
        query = query.join(models.MovieTag).join(models.Tag).filter(
            models.Tag.name == theme, models.Tag.category == "theme"
        )
    if audience:
        query = query.join(models.MovieTag).join(models.Tag).filter(
            models.Tag.name == audience, models.Tag.category == "audience"
        )
    if min_rating is not None:
        query = query.filter(
            or_(
                models.Movie.rating_domestic >= min_rating,
                models.Movie.rating_international >= min_rating,
            )
        )
    movies = query.order_by(models.Movie.rating_international.desc()).limit(limit).all()
    return [_to_brief(m) for m in movies]


def search_movies(
    db: Session,
    q: str,
    theme: str | None = None,
    audience: str | None = None,
    min_rating: float | None = None,
    limit: int = 10,
) -> list[MovieBrief]:
    """混合搜索：过滤条件 + 关键字/语义综合排序。"""
    # 先用过滤条件拿到候选集（不设 limit，全部参与排序）
    query = db.query(models.Movie)
    if theme:
        query = query.join(models.MovieTag).join(models.Tag).filter(
            models.Tag.name == theme, models.Tag.category == "theme"
        )
    if audience:
        query = query.join(models.MovieTag).join(models.Tag).filter(
            models.Tag.name == audience, models.Tag.category == "audience"
        )
    if min_rating is not None:
        query = query.filter(
            or_(
                models.Movie.rating_domestic >= min_rating,
                models.Movie.rating_international >= min_rating,
            )
        )
    candidates = query.all()
    if not candidates:
        return []

    recommender._index.ensure(db)
    qvec = embeddings.embed_text(q)

    scored: list[tuple[float, models.Movie]] = []
    for movie in candidates:
        sem = 0.0
        if movie.id in recommender._index.text_map:
            idx = recommender._index.ids.index(movie.id)
            sem = embeddings.cosine(qvec, recommender._index.vectors[idx])
        kw = _keyword_score(movie, q)
        score = 0.7 * max(sem, kw) + 0.3 * min(sem + kw, 1.0)
        scored.append((score, movie))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_to_brief(m) for _, m in scored[:limit]]
