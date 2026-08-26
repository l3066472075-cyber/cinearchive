"""FastAPI 应用入口。

启动：uvicorn app.main:app --reload --port 8000
文档：http://127.0.0.1:8000/docs
前端：http://127.0.0.1:8000/
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import auth, export, feedback, match, meta, movies, notes, progress, recommend, search, sessions
from .seed import init_db

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "影视教育资源库 API —— 集结好电影的深度档案，"
        "用于影视教育 + 艺术治疗。核心能力：把「情绪/境遇自述」翻译成电影推荐，"
        "并把每一次搜索/反馈转化为资源库的迭代原料。"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 业务路由
app.include_router(auth.router)
app.include_router(recommend.router)
app.include_router(search.router)
app.include_router(movies.router)
app.include_router(feedback.router)
app.include_router(notes.router)
app.include_router(progress.router)
app.include_router(sessions.router)
app.include_router(match.router)
app.include_router(export.router)
app.include_router(meta.router)

# 静态前端
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/v1", include_in_schema=False)
def api_root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
