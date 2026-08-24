"""共修观影 / 影领家带领：场次（开场、报名、列表）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, models
from ..db import get_db
from ..schemas import SessionCreate, SessionResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _to_response(db: Session, s: models.Session, user_id: int | None) -> SessionResponse:
    movie = db.get(models.Movie, s.movie_id)
    facilitator = db.get(models.User, s.facilitator_id)
    signup_count = (
        db.query(models.SessionSignup)
        .filter(models.SessionSignup.session_id == s.id)
        .count()
    )
    joined = False
    if user_id:
        joined = (
            db.query(models.SessionSignup)
            .filter(
                models.SessionSignup.session_id == s.id,
                models.SessionSignup.user_id == user_id,
            )
            .first()
            is not None
        )
    return SessionResponse(
        id=s.id,
        movie_id=s.movie_id,
        movie_title=movie.title if movie else "",
        facilitator_city=facilitator.city if facilitator else "",
        theme=s.theme,
        description=s.description,
        mode=s.mode,
        start_at=s.start_at,
        status=s.status,
        signup_count=signup_count,
        joined=joined,
        created_at=s.created_at,
    )


@router.post("", response_model=SessionResponse)
def create_session(
    req: SessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """影领家开场次。"""
    if db.get(models.Movie, req.movie_id) is None:
        raise HTTPException(status_code=404, detail="影片不存在")
    s = models.Session(
        facilitator_id=user.id,
        movie_id=req.movie_id,
        theme=req.theme,
        description=req.description,
        mode=req.mode,
        start_at=req.start_at,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_response(db, s, user.id)


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """列出开放中的场次。"""
    sessions = (
        db.query(models.Session)
        .filter(models.Session.status == "open")
        .order_by(models.Session.created_at.desc())
        .all()
    )
    return [_to_response(db, s, user.id if user else None) for s in sessions]


@router.post("/{session_id}/join", response_model=SessionResponse)
def join_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """寻影者报名入座。"""
    s = db.get(models.Session, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="场次不存在")
    exists = (
        db.query(models.SessionSignup)
        .filter(
            models.SessionSignup.session_id == session_id,
            models.SessionSignup.user_id == user.id,
        )
        .first()
    )
    if not exists:
        db.add(models.SessionSignup(session_id=session_id, user_id=user.id))
        db.commit()
    return _to_response(db, s, user.id)


@router.post("/{session_id}/leave", response_model=SessionResponse)
def leave_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    """取消报名。"""
    s = db.get(models.Session, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="场次不存在")
    db.query(models.SessionSignup).filter(
        models.SessionSignup.session_id == session_id,
        models.SessionSignup.user_id == user.id,
    ).delete()
    db.commit()
    return _to_response(db, s, user.id)
