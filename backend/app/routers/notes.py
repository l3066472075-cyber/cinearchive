"""「观电影法」笔记接口：观影笔记(viewer) / 复盘笔记(facilitator)。

笔记提交后，后端调用大模型生成深度专属回应；笔记沉淀为「自循环」原料。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth, models
from ..ai import llm
from ..config import settings
from ..db import get_db
from ..schemas import NoteCreate, NoteResponse

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])


@router.post("", response_model=NoteResponse)
def create_note(
    req: NoteCreate,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """提交笔记 → 生成大模型深度专属回应。"""
    movie_title = ""
    if req.movie_id:
        movie = db.get(models.Movie, req.movie_id)
        movie_title = movie.title if movie else ""

    llm_text = llm.respond_to_note(req.role, req.content, movie_title)
    response = llm_text or llm.template_note_response(req.role, req.content, movie_title)

    note = models.Note(
        user_id=user.id if user else None,
        movie_id=req.movie_id,
        role=req.role,
        content=req.content,
        llm_response=response,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=note.id,
        role=note.role,
        movie_id=note.movie_id,
        content=note.content,
        llm_response=note.llm_response,
        engine="llm" if settings.llm_enabled else "offline",
        created_at=note.created_at,
    )


@router.get("", response_model=list[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    user: models.User | None = Depends(auth.get_current_user_optional),
):
    """列出当前用户的笔记（未登录则返回公开笔记为空）。"""
    q = db.query(models.Note)
    if user:
        q = q.filter(models.Note.user_id == user.id)
    else:
        q = q.filter(models.Note.id == -1)  # 未登录返回空
    return [
        NoteResponse(
            id=n.id,
            role=n.role,
            movie_id=n.movie_id,
            content=n.content,
            llm_response=n.llm_response,
            engine="llm" if settings.llm_enabled else "offline",
            created_at=n.created_at,
        )
        for n in q.order_by(models.Note.created_at.desc()).all()
    ]
