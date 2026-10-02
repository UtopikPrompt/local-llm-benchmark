"""Persistence layer: SQLAlchemy models and helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

DATABASE_URL = "sqlite:///./benchmark.db"
_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JudgeModel(Base):
    """A judge model definition used to score LLM responses."""

    __tablename__ = "judges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    runs: Mapped[list["Run"]] = relationship(back_populates="judge")


class RunStatus(str, SAEnum):  # noqa: F821
    """Lifecycle states for a benchmark run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(Base):
    """A single benchmark execution."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    judge_id: Mapped[int | None] = mapped_column(
        ForeignKey("judges.id"), nullable=True
    )
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus), default=RunStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    judge: Mapped["JudgeModel | None"] = relationship(back_populates="runs")
    result: Mapped["RunResult | None"] = relationship(
        back_populates="run", uselist=False
    )


class RunResult(Base):
    """A scored result produced for a completed run."""

    __tablename__ = "run_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id"), unique=True, nullable=False
    )
    score: Mapped[int] = mapped_column(nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    run: Mapped[Run] = relationship(back_populates="result")


def init_db() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=_engine)


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def session() -> Session:
    """Return a new ORM session."""
    return SessionLocal()