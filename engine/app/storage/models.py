"""ORM models for the storage layer."""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.storage.db import Base


class Model(Base):
    """Abstract base providing common columns for every model."""

    __abstract__ = True

    created_at = Column(DateTime, default=_dt.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=_dt.datetime.utcnow,
        onupdate=_dt.datetime.utcnow,
        nullable=False,
    )


class Run(Model):
    """A single benchmark execution."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    error = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ModelInfo(Model):
    """Metadata describing an LLM that can be benchmarked."""

    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    provider = Column(String(128), nullable=True)
    max_tokens = Column(Integer, nullable=True)


class Result(Model):
    """The outcome of running a model against a benchmark run."""

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("runs.id"),
        nullable=False,
        index=True,
    )
    model_id = Column(
        Integer,
        ForeignKey("models.id"),
        nullable=True,
        index=True,
    )
    score = Column(Float, nullable=True)
    metrics = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)