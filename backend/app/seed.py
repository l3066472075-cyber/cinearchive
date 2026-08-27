"""数据初始化：建表 + 写入种子数据（标签 + 影片档案）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import models
from .db import Base, engine
from .seed_data import MOVIES, TAGS


def _validate() -> None:
    """校验影片档案里引用的标签都已在 TAGS 注册，避免脏数据。"""
    for movie in MOVIES:
        for tag in movie["tags"]:
            if tag not in TAGS:
                raise ValueError(f"影片《{movie['title']}》引用了未注册的标签「{tag}」")


def sync_tags(db: Session) -> None:
    """影片已存在时，增量同步新增的标签 + 影片标签关联（用于线上无痛升级）。"""
    # 1) 补齐标签
    for name, (category, desc) in TAGS.items():
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if tag is None:
            db.add(models.Tag(name=name, category=category, description=desc, source="curated"))
    db.flush()

    # 2) 补齐影片-标签关联
    for m in MOVIES:
        movie = db.query(models.Movie).filter(models.Movie.title == m["title"]).first()
        if movie is None:
            continue
        for tag_name in m["tags"]:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if tag is None:
                continue
            link = (
                db.query(models.MovieTag)
                .filter(models.MovieTag.movie_id == movie.id, models.MovieTag.tag_id == tag.id)
                .first()
            )
            if link is None:
                db.add(models.MovieTag(movie_id=movie.id, tag_id=tag.id, weight=1.0, source="curated"))
    db.commit()
    print(f"[seed] 标签同步完成：共 {db.query(models.Tag).count()} 个标签。")


def seed(db: Session) -> None:
    _validate()
    existing = db.query(models.Movie).count()
    if existing:
        print(f"[seed] 库中已有 {existing} 部影片，执行增量标签同步。")
        sync_tags(db)
        return

    # 1) 建标签
    tag_map: dict[str, models.Tag] = {}
    for name, (category, desc) in TAGS.items():
        tag = models.Tag(name=name, category=category, description=desc, source="curated")
        db.add(tag)
        tag_map[name] = tag
    db.flush()

    # 2) 建影片 + 关联标签
    for m in MOVIES:
        movie = models.Movie(
            title=m["title"],
            title_en=m["title_en"],
            year=m["year"],
            director=m["director"],
            cast=m["cast"],
            country=m["country"],
            duration_min=m["duration_min"],
            genres=m["genres"],
            release_date=m["release_date"],
            rating_domestic=m["rating_domestic"],
            rating_international=m["rating_international"],
            synopsis=m["synopsis"],
            deep_analysis=m["deep_analysis"],
            support_audiences=m["support_audiences"],
            support_types=m["support_types"],
            therapy_notes=m["therapy_notes"],
            trigger_warnings=m["trigger_warnings"],
            discussion_questions=m["discussion_questions"],
        )
        db.add(movie)
        db.flush()
        for tag_name in m["tags"]:
            db.add(
                models.MovieTag(
                    movie_id=movie.id,
                    tag_id=tag_map[tag_name].id,
                    weight=1.0,
                    source="curated",
                )
            )

    db.commit()
    print(f"[seed] 初始化完成：{len(TAGS)} 个标签，{len(MOVIES)} 部影片。")


def _migrate_columns() -> None:
    """给已有表补齐缺失的列（create_all 不会给旧表加列，需要手动 ALTER）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    try:
        with engine.begin() as conn:
            table_names = insp.get_table_names()
            if "users" in table_names:
                cols = {c["name"] for c in insp.get_columns("users")}
                if "phone" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT ''"))
                    print("[migrate] users 表已补 phone 列")
                if "city" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN city VARCHAR(50) DEFAULT ''"))
                    print("[migrate] users 表已补 city 列")
    except Exception as e:  # noqa: BLE001
        print(f"[migrate] 跳过迁移：{e}")


def init_db() -> None:
    """建表 + 迁移缺失列 + 写入种子数据（幂等）。"""
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    from .db import SessionLocal

    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    init_db()
