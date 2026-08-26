"""Pydantic Schema：API 的输入输出契约。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------- 标签 ----------
class TagOut(BaseModel):
    id: int
    name: str
    category: str
    description: str = ""
    use_count: int = 0

    model_config = {"from_attributes": True}


# ---------- 影片 ----------
class MovieBrief(BaseModel):
    id: int
    title: str
    title_en: str = ""
    year: int
    director: str = ""
    country: str = ""
    genres: list[str] = []
    rating_domestic: float = 0.0
    rating_international: float = 0.0
    synopsis: str = ""

    model_config = {"from_attributes": True}


class MovieDetail(MovieBrief):
    cast: list[str] = []
    duration_min: int = 0
    release_date: str = ""
    rating_domestic_source: str = "豆瓣"
    rating_international_source: str = "IMDb"
    deep_analysis: dict[str, Any] = {}
    support_audiences: list[str] = []
    support_types: list[str] = []
    therapy_notes: str = ""
    trigger_warnings: list[str] = []
    discussion_questions: list[str] = []
    cover_url: Optional[str] = None
    tags: list[TagOut] = []


# ---------- 推荐 ----------
class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户的情绪/境遇描述，例如：我现在很无力，和青春期孩子交流不顺")
    limit: int = Field(5, ge=1, le=20)
    audience: Optional[str] = Field(None, description="可选：指定支持人群，如「青春期孩子父母」")
    with_explanation: bool = Field(True, description="是否生成推荐理由")


class RecommendItem(BaseModel):
    movie: MovieDetail
    score: float = Field(..., description="匹配度 0-1")
    matched_tags: list[str] = []
    explanation: str = ""


class RecommendResponse(BaseModel):
    query: str
    intent_labels: list[str] = []
    items: list[RecommendItem] = []
    engine: str = "offline"  # offline / llm
    search_log_id: Optional[int] = None
    note: str = ""


# ---------- 双角色 · 5 问引导推荐 ----------
class GuidedRequest(BaseModel):
    role: str = Field(..., description="viewer（寻影者）| facilitator（影领家）")
    answers: dict[str, str] = Field(
        ..., description="5 个维度的答案：emotion/situation/value/audience/theme → 标签名"
    )
    limit: int = Field(5, ge=1, le=20)


class GuidedResponse(BaseModel):
    role: str
    intent_labels: list[str] = []
    items: list[RecommendItem] = []
    interpretation: str = ""  # 角色化的解读/指引（大模型生成，无 key 时模板）
    engine: str = "offline"
    search_log_id: Optional[int] = None


# ---------- 搜索 ----------
class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)
    theme: Optional[str] = None
    audience: Optional[str] = None
    min_rating: Optional[float] = None


class SearchResponse(BaseModel):
    q: str
    items: list[MovieBrief] = []
    total: int = 0
    search_log_id: Optional[int] = None


# ---------- 反馈 ----------
class FeedbackRequest(BaseModel):
    search_log_id: Optional[int] = None
    movie_id: int
    helpful: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: str = ""
    suggested_tag: str = ""


class FeedbackResponse(BaseModel):
    id: int
    status: str = "new"
    applied_tags: list[str] = []
    message: str = ""


# ---------- 统计 / 洞察 ----------
class Insight(BaseModel):
    top_queries: list[dict[str, Any]] = []
    emerging_needs: list[dict[str, Any]] = []
    pending_tag_suggestions: list[str] = []
    total_searches: int = 0
    total_movies: int = 0
    total_tags: int = 0


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    llm_enabled: bool
    embedding_enabled: bool
    wx_enabled: bool = False
    movies: int
    tags: int
    searches: int


# ---------- 鉴权（微信静默登录） ----------
class WxLoginRequest(BaseModel):
    code: str = Field(..., description="wx.login() 返回的临时凭证 code")
    nickname: str = ""
    avatar_url: str = ""


class WxLoginResponse(BaseModel):
    token: str
    openid: str
    is_new_user: bool = False
    wx_enabled: bool = False


class MeResponse(BaseModel):
    id: int
    openid: str
    nickname: str = ""
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


# ---------- 「观电影法」笔记 ----------
class NoteCreate(BaseModel):
    role: str = Field(..., description="viewer（观影笔记）| facilitator（复盘笔记）")
    movie_id: Optional[int] = None
    content: dict[str, Any] = Field(..., description="笔记各字段（结构化 JSON）")


class NoteResponse(BaseModel):
    id: int
    role: str
    movie_id: Optional[int] = None
    content: dict[str, Any] = {}
    llm_response: str = ""
    engine: str = "offline"
    created_at: Optional[datetime] = None


# ---------- 观心成长（段位/印记/打卡/城市） ----------
class CheckInRequest(BaseModel):
    date: str = ""  # YYYY-MM-DD，留空用今天
    movie_id: Optional[int] = None
    note: str = ""


class CheckInResponse(BaseModel):
    ok: bool = True
    date: str = ""
    lit_days: int = 0  # 已点亮天数
    message: str = ""


class CityUpdate(BaseModel):
    city: str = Field(..., min_length=1, max_length=50)


class ProgressResponse(BaseModel):
    level: int
    level_name: str
    level_desc: str
    next_level_name: str
    progress_pct: int  # 到下一级进度 0-100
    badges: list[dict[str, Any]] = []
    checkin_days: int = 0
    checkin_streak: int = 0
    search_count: int = 0
    note_count: int = 0
    city: str = ""


# ---------- 共修观影 / 影领家带领（场次） ----------
class SessionCreate(BaseModel):
    movie_id: int
    theme: str = ""
    description: str = ""
    mode: str = Field("sync", description="sync 同步 / async 异步")
    start_at: str = ""


class SessionResponse(BaseModel):
    id: int
    movie_id: int
    movie_title: str = ""
    facilitator_city: str = ""
    theme: str = ""
    description: str = ""
    mode: str = "sync"
    start_at: str = ""
    status: str = "open"
    signup_count: int = 0
    joined: bool = False
    created_at: Optional[datetime] = None


# ---------- 同频影友匹配 ----------
class MatchResponse(BaseModel):
    city: str = ""
    same_city_count: int = 0
    my_tags: list[str] = []
    resonance: list[dict[str, Any]] = []


# ---------- 导出 PPT ----------
class PptExportRequest(BaseModel):
    answers: dict[str, str] = {}
    movies: list[dict[str, Any]] = []
