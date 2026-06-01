from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    target_duration: Mapped[str] = mapped_column(String(64), nullable=False)
    style: Mapped[str] = mapped_column(String(64), nullable=False)
    pacing: Mapped[str] = mapped_column(String(64), nullable=False)
    needs_hook: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_broll: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_research_visuals: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subtitle(Base):
    __tablename__ = "subtitles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cue_count: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    keyframe_paths: Mapped[str] = mapped_column(Text, default="[]")
    user_tags: Mapped[str] = mapped_column(Text, default="[]")
    ai_tags: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Storyboard(Base):
    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, unique=True, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, unique=True, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DraftExport(Base):
    __tablename__ = "draft_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    output_path: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
