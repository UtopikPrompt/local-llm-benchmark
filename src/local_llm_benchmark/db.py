"""Database module with query optimization and connection management.

This module provides:
- Query optimization (indexes, caching, pagination)
- Connection management (timeouts, health checks, graceful shutdown)
- Declarative models for benchmark results
- CRUD operations with performance considerations
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Text,
    create_async_engine,
    event,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import select

from ..config import AppConfig
from ..cache import ResponseCache


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class DBConfig:
    """Database configuration with connection management settings."""
    url: str = field(default="sqlite:///./benchmark.db")
    pool_size: int = field(default=10)
    max_overflow: int = field(default=20)
    connect_timeout: float = field(default=30.0)  # Connection timeout in seconds
    query_timeout: float = field(default=300.0)  # Query timeout in seconds
    health_check_interval: float = field(default=60.0)  # Health check interval in seconds


# ============================================================================
# Database Manager
# ============================================================================

class DBManager:
    """Manages database connections with health checks and graceful shutdown."""

    def __init__(self, config: AppConfig):
        """Initialize database manager.
        
        Args:
            config: Application configuration with database settings
        """
        self.config = config
        self._engine: Optional[asyncio.AbstractEventLoop] = None
        self._session_maker: Optional[async_sessionmaker] = None
        self._cache: Optional[ResponseCache] = None
        self._shutdown_event = asyncio.Event()
        self._shutdown_complete = False

    async def initialize(self) -> None:
        """Initialize the database connection and cache."""
        logger.info("Initializing database manager")
        
        # Create async engine with connection pooling
        engine = create_async_engine(
            self.config.db.url,
            pool_size=self.config.db.pool_size,
            max_overflow=self.config.db.max_overflow,
            connect_timeout=self.config.db.connect_timeout,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Disable SQL logging for production
        )
        
        # Create session maker
        self._session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Initialize response cache
        self._cache = ResponseCache(
            ttl=self.config.cache_ttl,
            max_size=10000,
        )

    async def initialize_tables(self, metadata: MetaData) -> None:
        """Create database tables if they don't exist."""
        async with self._session_maker() as session:
            await session.execute(metadata.create_all())
            logger.info("Database tables initialized")

    @asynccontextmanager
    async def get_session(self):
        """Get a database session with automatic cleanup.
        
        Usage:
            async with db_manager.get_session() as session:
                async with session:
                    # Your database operations here
                    pass
        """
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Gracefully close all database connections and resources."""
        logger.info("Closing database manager")
        
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        
        if self._session_maker:
            self._session_maker.close()
            self._session_maker = None
        
        if self._cache:
            await self._cache.close()
            self._cache = None
        
        self._shutdown_event.set()
        self._shutdown_complete = True
        logger.info("Database manager closed")

    async def health_check(self) -> bool:
        """Check if the database connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                async with session:
                    # Simple ping query
                    result = await session.execute(select(1))
                    return result.fetchone() is not None
        except Exception:
            logger.error("Database health check failed", exc_info=True)
            return False

    async def start_health_checks(self) -> None:
        """Start background health check task."""
        async def health_check_loop():
            while not self._shutdown_complete:
                await asyncio.sleep(self.config.db.health_check_interval)
                if not await self.health_check():
                    logger.error("Database health check failed")
                    # Optionally reconnect or alert here
        
        self._shutdown_event = asyncio.Event()
        asyncio.create_task(health_check_loop())

    async def shutdown(self) -> None:
        """Wait for shutdown to complete."""
        await self._shutdown_event.wait()


# ============================================================================
# Declarative Base
# ============================================================================

class Base(DeclarativeBase):
    """Custom declarative base with JSON support for SQLite."""

    metadata = MetaData()

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, created_at={self.created_at})"


# ============================================================================
# Models
# ============================================================================

@dataclass
class BenchmarkResult:
    """Benchmark result dataclass.
    
    This represents a single benchmark result with all fields needed
    for storage and query optimization.
    """
    id: int = 0
    challenge_id: int = 0
    engine_id: int = 0
    task_id: int = 0
    quality_score: float = 0.0
    accuracy: Optional[float] = None
    inference_time_ms: Optional[float] = None
    tokens_per_second: Optional[float] = None
    completion_time_ms: Optional[float] = None
    context_window_tokens: Optional[int] = None
    temperature: Optional[float] = None
    model_name: Optional[str] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "challenge_id": self.challenge_id,
            "engine_id": self.engine_id,
            "task_id": self.task_id,
            "quality_score": self.quality_score,
            "accuracy": self.accuracy,
            "inference_time_ms": self.inference_time_ms,
            "tokens_per_second": self.tokens_per_second,
            "completion_time_ms": self.completion_time_ms,
            "context_window_tokens": self.context_window_tokens,
            "temperature": self.temperature,
            "model_name": self.model_name,
            "prompt": self.prompt,
            "completion": self.completion,
            "raw_response": self.raw_response,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BenchmarkResult(Base):
    """Database model for benchmark results."""

    __tablename__ = "benchmark_results"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("engines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    quality_score: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, index=True
    )
    accuracy: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    inference_time_ms: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    tokens_per_second: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    completion_time_ms: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    context_window_tokens: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    temperature: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 4), nullable=True
    )
    model_name: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    challenge = relationship("Challenge", back_populates="results")
    engine = relationship("Engine", back_populates="results")


class Challenge(Base):
    """Database model for challenges."""

    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_completion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )


class Engine(Base):
    """Database model for engines."""

    __tablename__ = "engines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )


# ============================================================================
# Database Operations
# ============================================================================

class Database:
    """Database operations with caching and pagination."""

    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self._cache = ResponseCache(
            ttl=db_manager.config.cache_ttl,
            max_size=10000,
        )

    async def get_session(self):
        """Get a database session."""
        async with self.db_manager.get_session() as session:
            async with session:
                yield session

    # ========================================================================
    # CRUD Operations - Results
    # ========================================================================

    async def create_result(
        self,
        challenge_id: int,
        engine_id: int,
        task_id: int,
        quality_score: float,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a benchmark result.
        
        Args:
            challenge_id: ID of the challenge
            engine_id: ID of the engine
            task_id: ID of the task
            quality_score: Quality score (0-1)
            **kwargs: Additional result fields
        
        Returns:
            The created result as a dictionary
        """
        async with self.get_session() as session:
            async with session:
                result = BenchmarkResult(
                    challenge_id=challenge_id,
                    engine_id=engine_id,
                    task_id=task_id,
                    quality_score=quality_score,
                    **kwargs,
                )
                session.add(result)
                await session.flush()
                await session.refresh(result)
                
                # Cache the result for fast retrieval
                cache_key = self._get_cache_key(result)
                await self._cache.set(cache_key, result.to_dict())
                
                logger.debug(f"Created benchmark result {result.id}")
                return result.to_dict()

    async def get_result(self, result_id: int) -> Optional[dict[str, Any]]:
        """Get a benchmark result by ID with caching.
        
        Args:
            result_id: The result ID
        
        Returns:
            The result as a dictionary or None
        """
        # Check cache first
        cache_key = self._get_cache_key(BenchmarkResult(id=result_id))
        cached = await self._cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for result {result_id}")
            return cached
        
        async with self.get_session() as session:
            async with session:
                result = await session.get(BenchmarkResult, result_id)
                if result:
                    await session.refresh(result)
                    # Cache the result
                    await self._cache.set(cache_key, result.to_dict())
                    logger.debug(f"Fetched and cached benchmark result {result_id}")
                    return result.to_dict()
        
        return None

    async def get_results_by_challenge(
        self,
        challenge_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
    ) -> list[dict[str, Any]]:
        """Get results for a specific challenge with pagination.
        
        Args:
            challenge_id: The challenge ID
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order by (default: created_at DESC)
        
        Returns:
            List of result dictionaries
        """
        order_map = {
            "created_at": "created_at DESC",
            "updated_at": "updated_at DESC",
            "quality_score": "quality_score DESC",
            "accuracy": "accuracy DESC",
            "inference_time_ms": "inference_time_ms ASC",
            "completion_time_ms": "completion_time_ms ASC",
        }
        
        order_by_clause = order_map.get(order_by, "created_at DESC")
        
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .where(BenchmarkResult.challenge_id == challenge_id)
                    .order_by(order_by_clause)
                    .limit(limit)
                    .offset(offset)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
                
                # Cache results
        
        return [r.to_dict() for r in result_objects]

    async def get_results_by_engine(
        self,
        engine_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
    ) -> list[dict[str, Any]]:
        """Get results for a specific engine with pagination.
        
        Args:
            engine_id: The engine ID
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order by (default: created_at DESC)
        """
        order_map = {
            "created_at": "created_at DESC",
            "updated_at": "updated_at DESC",
            "quality_score": "quality_score DESC",
            "accuracy": "accuracy DESC",
            "inference_time_ms": "inference_time_ms ASC",
            "completion_time_ms": "completion_time_ms ASC",
        }
        
        order_by_clause = order_map.get(order_by, "created_at DESC")
        
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .where(BenchmarkResult.engine_id == engine_id)
                    .order_by(order_by_clause)
                    .limit(limit)
                    .offset(offset)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
        
        return [r.to_dict() for r in result_objects]

    async def get_results_by_task(
        self,
        task_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
    ) -> list[dict[str, Any]]:
        """Get results for a specific task with pagination.
        
        Args:
            task_id: The task ID
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order by (default: created_at DESC)
        """
        order_map = {
            "created_at": "created_at DESC",
            "updated_at": "updated_at DESC",
            "quality_score": "quality_score DESC",
            "accuracy": "accuracy DESC",
            "inference_time_ms": "inference_time_ms ASC",
            "completion_time_ms": "completion_time_ms ASC",
        }
        
        order_by_clause = order_map.get(order_by, "created_at DESC")
        
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .where(BenchmarkResult.task_id == task_id)
                    .order_by(order_by_clause)
                    .limit(limit)
                    .offset(offset)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
        
        return [r.to_dict() for r in result_objects]

    async def get_results_by_quality_range(
        self,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get results within a quality score range.
        
        Args:
            min_score: Minimum quality score
            max_score: Maximum quality score
            limit: Maximum number of results to return
            offset: Number of results to skip
        
        Returns:
            List of result dictionaries
        """
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .where(
                        (BenchmarkResult.quality_score >= min_score) &
                        (BenchmarkResult.quality_score <= max_score)
                    )
                    .order_by(BenchmarkResult.quality_score DESC)
                    .limit(limit)
                    .offset(offset)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
        
        return [r.to_dict() for r in result_objects]

    async def get_results_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get results within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of results to return
            offset: Number of results to skip
        
        Returns:
            List of result dictionaries
        """
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .where(
                        (BenchmarkResult.created_at >= start_date) &
                        (BenchmarkResult.created_at <= end_date)
                    )
                    .order_by(BenchmarkResult.created_at DESC)
                    .limit(limit)
                    .offset(offset)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
        
        return [r.to_dict() for r in result_objects]

    # ========================================================================
    # CRUD Operations - Aggregates
    # ========================================================================

    async def get_aggregate_stats(
        self,
        challenge_id: Optional[int] = None,
        engine_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Get aggregate statistics for benchmark results.
        
        Args:
            challenge_id: Filter by challenge
            engine_id: Filter by engine
            task_id: Filter by task
        
        Returns:
            Dictionary with aggregate statistics
        """
        async with self.get_session() as session:
            async with session:
                query = select(
                    func.count(BenchmarkResult.id).label("count"),
                    func.avg(BenchmarkResult.quality_score).label("avg_quality"),
                    func.max(BenchmarkResult.quality_score).label("max_quality"),
                    func.min(BenchmarkResult.quality_score).label("min_quality"),
                    func.stddev(BenchmarkResult.quality_score).label("stddev_quality"),
                )
                
                # Add filters
                if challenge_id:
                    query = query.where(BenchmarkResult.challenge_id == challenge_id)
                if engine_id:
                    query = query.where(BenchmarkResult.engine_id == engine_id)
                if task_id:
                    query = query.where(BenchmarkResult.task_id == task_id)
                
                results = await session.execute(query)
                row = results.fetchone()
                
                return {
                    "count": row.count,
                    "avg_quality": float(row.avg_quality) if row.avg_quality else None,
                    "max_quality": float(row.max_quality) if row.max_quality else None,
                    "min_quality": float(row.min_quality) if row.min_quality else None,
                    "stddev_quality": float(row.stddev_quality) if row.stddev_quality else None,
                }

    async def get_top_results(
        self,
        limit: int = 10,
        order_by: str = "quality_score",
    ) -> list[dict[str, Any]]:
        """Get top results by quality score.
        
        Args:
            limit: Number of results to return
            order_by: Field to order by
        
        Returns:
            List of top result dictionaries
        """
        order_map = {
            "quality_score": "quality_score DESC",
            "accuracy": "accuracy DESC",
            "inference_time_ms": "inference_time_ms ASC",
        }
        
        order_by_clause = order_map.get(order_by, "quality_score DESC")
        
        async with self.get_session() as session:
            async with session:
                query = select(BenchmarkResult)
                    .order_by(order_by_clause)
                    .limit(limit)
                
                results = await session.execute(query)
                result_objects = results.scalars().all()
        
        return [r.to_dict() for r in result_objects]

    # ========================================================================
    # CRUD Operations - Challenges
    # ========================================================================

    async def create_challenge(
        self,
        name: str,
        description: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a challenge.
        
        Args:
            name: Challenge name
            description: Challenge description
            **kwargs: Additional fields
        
        Returns:
            The created challenge as a dictionary
        """
        async with self.get_session() as session:
            async with session:
                challenge = Challenge(
                    name=name,
                    description=description,
                    **kwargs,
                )
                session.add(challenge)
                await session.flush()
                await session.refresh(challenge)
                
                logger.debug(f"Created challenge {challenge.id}")
                return challenge.to_dict()

    async def get_challenge(self, challenge_id: int) -> Optional[dict[str, Any]]:
        """Get a challenge by ID with caching."""
        async with self.get_session() as session:
            async with session:
                challenge = await session.get(Challenge, challenge_id)
                if challenge:
                    await session.refresh(challenge)
                    logger.debug(f"Fetched challenge {challenge_id}")
                    return challenge.to_dict()
        
        return None

    async def get_challenges(
        self,
        limit: int = 100,
        offset: int = 0,
        name: Optional[str] = None,
        difficulty: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get challenges with optional filtering and pagination."""
        async with self.get_session() as session:
            async with session:
                query = select(Challenge)
                    .order_by(Challenge.name)
                    .limit(limit)
                    .offset(offset)
                
                # Add filters
                if name:
                    query = query.where(Challenge.name.ilike(f"%{name}%"))
                if difficulty is not None:
                    query = query.where(Challenge.difficulty == difficulty)
                
                results = await session.execute(query)
                challenges = results.scalars().all()
        
        return [c.to_dict() for c in challenges]

    # ========================================================================
    # CRUD Operations - Engines
    # ========================================================================

    async def create_engine(
        self,
        name: str,
        engine_type: str,
        configuration: Optional[dict] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create an engine."""
        async with self.get_session() as session:
            async with session:
                engine = Engine(
                    name=name,
                    type=engine_type,
                    configuration=configuration,
                    **kwargs,
                )
                session.add(engine)
                await session.flush()
                await session.refresh(engine)
                
                logger.debug(f"Created engine {engine.id}")
                return engine.to_dict()

    async def get_engine(self, engine_id: int) -> Optional[dict[str, Any]]:
        """Get an engine by ID."""
        async with self.get_session() as session:
            async with session:
                engine = await session.get(Engine, engine_id)
                if engine:
                    await session.refresh(engine)
                    logger.debug(f"Fetched engine {engine_id}")
                    return engine.to_dict()
        
        return None

    async def get_engines(
        self,
        limit: int = 100,
        offset: int = 0,
        engine_type: Optional[str] = None,
        active: bool = None,
    ) -> list[dict[str, Any]]:
        """Get engines with optional filtering and pagination."""
        async with self.get_session() as session:
            async with session:
                query = select(Engine)
                    .order_by(Engine.name)
                    .limit(limit)
                    .offset(offset)
                
                # Add filters
                if engine_type:
                    query = query.where(Engine.type == engine_type)
                if active is not None:
                    query = query.where(Engine.is_active == active)
                
                results = await session.execute(query)
                engines = results.scalars().all()
        
        return [e.to_dict() for e in engines]

    async def update_result(
        self,
        result_id: int,
        **kwargs,
    ) -> Optional[dict[str, Any]]:
        """Update a benchmark result.
        
        Args:
            result_id: The result ID to update
            **kwargs: Fields to update
        
        Returns:
            The updated result as a dictionary
        """
        async with self.get_session() as session:
            async with session:
                result = await session.get(BenchmarkResult, result_id)
                if result:
                    for key, value in kwargs.items():
                        if hasattr(result, key):
                            setattr(result, key, value)
                    await session.flush()
                    await session.refresh(result)
                    
                    # Update cache
                    cache_key = self._get_cache_key(result)
                    await self._cache.set(cache_key, result.to_dict())
                    
                    logger.debug(f"Updated benchmark result {result_id}")
                    return result.to_dict()
        
        return None

    async def delete_result(self, result_id: int) -> bool:
        """Delete a benchmark result."""
        async with self.get_session() as session:
            async with session:
                result = await session.get(BenchmarkResult, result_id)
                if result:
                    session.delete(result)
                    await session.commit()
                    
                    # Invalidate cache
                    cache_key = self._get_cache_key(result)
                    await self._cache.delete(cache_key)
                    
                    logger.debug(f"Deleted benchmark result {result_id}")
                    return True
        
        return False

    # ========================================================================
    # Cache Helpers
    # ========================================================================

    def _get_cache_key(self, result: BenchmarkResult) -> str:
        """Generate a cache key for a result."""
        key_data = f"result:{result.id}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def invalidate_cache(self, challenge_id: Optional[int] = None) -> None:
        """Invalidate cache entries."""
        if challenge_id:
            # Invalidate all results for a specific challenge
            async with self.get_session() as session:
                async with session:
                    results = await session.execute(
                        select(BenchmarkResult).where(
                            BenchmarkResult.challenge_id == challenge_id
                        )
                    )
                    result_ids = {r.id for r in results.scalars().all()}
                    
                    for result_id in result_ids:
                        cache_key = self._get_cache_key(
                            BenchmarkResult(id=result_id)
                        )
                        await self._cache.delete(cache_key)
        
        # Invalidate all cache
        await self._cache.close()
        self._cache = ResponseCache(
            ttl=self.db_manager.config.cache_ttl,
            max_size=10000,
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_db_manager: Optional[DBManager] = None
_db: Optional[Database] = None


def get_db_manager(config: AppConfig) -> DBManager:
    """Get or create a singleton DBManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DBManager(config)
    return _db_manager


def get_database(db_manager: DBManager) -> Database:
    """Get or create a singleton Database instance."""
    global _db
    if _db is None:
        _db = Database(db_manager)
    return _db


def get_db(config: AppConfig) -> tuple[DBManager, Database]:
    """Get singleton instances of DBManager and Database."""
    return get_db_manager(config), get_database(get_db_manager(config))


# ============================================================================
# Migration Helper
# ============================================================================

async def ensure_indexes(session: AsyncSession) -> None:
    """Ensure required indexes exist on the database."""
    async with session:
        # Check and create indexes
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_challenge_id ON benchmark_results(challenge_id)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_engine_id ON benchmark_results(engine_id)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_task_id ON benchmark_results(task_id)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_quality_score ON benchmark_results(quality_score)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_created_at ON benchmark_results(created_at)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_challenges_name ON challenges(name)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_engines_name ON engines(name)"
        )
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_engines_type ON engines(type)"
        )
        await session.commit()
        logger.info("Database indexes ensured")


if __name__ == "__main__":
    # Example usage
    import asyncio
    from config import AppConfig
    
    async def main():
        config = AppConfig()
        db_manager = get_db_manager(config)
        await db_manager.initialize()
        await db_manager.initialize_tables(Base.metadata)
        await ensure_indexes(db_manager._session_maker())
        db = get_database(db_manager)
        
        # Create a test result
        result = await db.create_result(
            challenge_id=1,
            engine_id=1,
            task_id=1,
            quality_score=0.95,
            accuracy=0.94,
            inference_time_ms=120.5,
            tokens_per_second=450.0,
            model_name="test-model",
        )
        print(f"Created result: {result}")
        
        # Get the result
        fetched = await db.get_result(result["id"])
        print(f"Fetched result: {fetched}")
        
        # Get results by challenge
        results = await db.get_results_by_challenge(challenge_id=1, limit=10)
        print(f"Results by challenge: {len(results)}")
        
        # Close
        await db.close()
        await db_manager.close()
    
    asyncio.run(main())
