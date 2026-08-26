"""数据模型：影片档案 + 情感/治疗维度标签 + 搜索自增长闭环。

核心设计原则：
1. 这是「好电影的深度档案库」，不存视频、不做流媒体——存的是元数据 + 深度解读 + 治疗维度。
2. 影片与「标签」多对多关联；标签按 category 分为：
   emotion(情感状态) / situation(人生境遇) / audience(支持人群) / value(价值资源) / theme(影片主题)。
3. 每次搜索/推荐都会写入 SearchLog；用户反馈写入 Feedback。
   二者共同构成「搜索即喂养」的原料，推动标签与影片档案不断迭代。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    # 返回「无时区的 UTC 时间」，兼容 SQLite 与 MySQL 的 DateTime 存储
    return datetime.now(timezone.utc).replace(tzinfo=None)


# 标签分类（情感/境遇/人群/价值/主题）
TAG_CATEGORIES = ("emotion", "situation", "audience", "value", "theme")


class Movie(Base):
    """一部影片的深度档案。"""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)  # 中文名
    title_en: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[int] = mapped_column(Integer, index=True)
    director: Mapped[str] = mapped_column(String(200), default="")
    cast: Mapped[list] = mapped_column(JSON, default=list)  # 主演
    country: Mapped[str] = mapped_column(String(100), default="")
    duration_min: Mapped[int] = mapped_column(Integer, default=0)
    genres: Mapped[list] = mapped_column(JSON, default=list)
    release_date: Mapped[str] = mapped_column(String(50), default="")

    # 国内外评分（豆瓣 / IMDb）
    rating_domestic: Mapped[float] = mapped_column(Float, default=0.0)
    rating_domestic_source: Mapped[str] = mapped_column(String(50), default="豆瓣")
    rating_international: Mapped[float] = mapped_column(Float, default=0.0)
    rating_international_source: Mapped[str] = mapped_column(String(50), default="IMDb")

    synopsis: Mapped[str] = mapped_column(Text, default="")

    # 深度解读（结构化 JSON）：theme 主题 / art_value 艺术价值 /
    #   edu_value 教育价值 / therapy_value 治疗价值
    deep_analysis: Mapped[dict] = mapped_column(JSON, default=dict)

    # —— 治疗/教育维度（核心创新）——
    support_audiences: Mapped[list] = mapped_column(JSON, default=list)  # 支持人群
    support_types: Mapped[list] = mapped_column(JSON, default=list)  # 支持方式
    therapy_notes: Mapped[str] = mapped_column(Text, default="")  # 观影治疗使用说明
    trigger_warnings: Mapped[list] = mapped_column(JSON, default=list)  # 触发预警
    discussion_questions: Mapped[list] = mapped_column(JSON, default=list)  # 讨论问题

    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    curated: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否人工精选

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    tags: Mapped[list["MovieTag"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )


class Tag(Base):
    """情感/境遇/人群/价值/主题标签（可查询、可增长的维度轴）。"""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", "category", name="uq_tag_name_category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)  # 见 TAG_CATEGORIES
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50), default="curated")  # curated / user / ai
    use_count: Mapped[int] = mapped_column(Integer, default=0)  # 被搜索/使用的热度

    movie_links: Mapped[list["MovieTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class MovieTag(Base):
    """影片-标签 关联，带权重（某标签对这部影片的重要性）。"""

    __tablename__ = "movie_tags"

    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(50), default="curated")  # curated / user / ai

    movie: Mapped["Movie"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="movie_links")


class User(Base):
    """用户（微信 openid 或 手机号 登录）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)  # 手机号登录
    nickname: Mapped[str] = mapped_column(String(100), default="")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    city: Mapped[str] = mapped_column(String(50), default="")  # 城市坐标（找同城人）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CheckIn(Base):
    """21天观电影法打卡践行：每天点亮一盏心灯。"""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_checkin_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")  # 今日观心一句话
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Session(Base):
    """共修观影场次：影领家开场，寻影者报名入座。"""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facilitator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    theme: Mapped[str] = mapped_column(String(200), default="")  # 场次主题
    description: Mapped[str] = mapped_column(Text, default="")  # 引导语/说明
    mode: Mapped[str] = mapped_column(String(20), default="sync")  # sync 同步 / async 异步
    start_at: Mapped[str] = mapped_column(String(50), default="")  # 时间（自由填写）
    status: Mapped[str] = mapped_column(String(20), default="open")  # open / closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SessionSignup(Base):
    """场次报名（寻影者入座）。"""

    __tablename__ = "session_signups"
    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_signup_session_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SearchLog(Base):
    """每一次搜索/推荐请求——「搜索即喂养」的原料。"""

    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    raw_query: Mapped[str] = mapped_column(Text, default="")
    normalized_query: Mapped[str] = mapped_column(Text, default="")
    intent_labels: Mapped[list] = mapped_column(JSON, default=list)  # 识别出的情感/境遇标签
    matched_movie_ids: Mapped[list] = mapped_column(JSON, default=list)  # 命中的影片 id
    chosen_movie_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="recommend")  # recommend / search
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Feedback(Base):
    """用户对推荐结果的反馈，可转化为标签/档案的增量贡献。"""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    search_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("search_logs.id"), nullable=True
    )
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    comment: Mapped[str] = mapped_column(Text, default="")
    suggested_tag: Mapped[str] = mapped_column(String(100), default="")  # 用户建议的新标签
    status: Mapped[str] = mapped_column(String(50), default="new")  # new / applied / rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Note(Base):
    """「观电影法」笔记：观影笔记(viewer) / 复盘笔记(facilitator)。

    笔记既是用户的个人记录，也是「自循环」的原料——沉淀后可反哺
    大模型的观影引导与带领建议，服务更多相似人群。
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # viewer / facilitator
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # 笔记各字段（结构化）
    llm_response: Mapped[str] = mapped_column(Text, default="")  # 大模型的深度专属回应
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
