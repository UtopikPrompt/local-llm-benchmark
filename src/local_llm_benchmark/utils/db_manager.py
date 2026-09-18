"""Database connection manager with async pooling using SQLAlchemy 2.0+."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool


class DBManager:
    """Async database connection manager with pooling."""
    
    def __init__(self, url: str, echo: bool = False):
        """Initialize the database manager with connection pooling.
        
        Args:
            url: Database URL (e.g., "postgresql+asyncpg://user:pass@host/db")
            echo: Whether to log SQL queries
        """
        self.url = url
        self.engine = create_async_engine(
            url,
            echo=echo,
            poolclass=QueuePool,
            pool_size=10,           # Minimum connections in pool
            max_overflow=20,        # Additional connections when pool exhausted
            pool_recycle=3600,      # Recycle connections after 1 hour
            pool_pre_ping=True,     # Verify connection before use
        )
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    async def get_db(self) -> AsyncSession:
        """Get a database session from the pool.
        
        Usage:
            async with db_manager.get_db() as session:
                # Use session here
        """
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close all connections in the pool."""
        await self.engine.dispose()


def check_pool_health(engine):
    """Monitor pool health and print current state.
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        Dictionary with pool metrics
    """
    pool = engine.pool
    
    async def _check_health():
        connections = await pool.size()
        checked_out = await pool.checkedout()
        overflow = await pool.overflow()
        
        print(f"Pool: {connections} total, {checked_out} checked out, {overflow} overflow")
        
        return {
            "total_connections": connections,
            "checked_out": checked_out,
            "overflow": overflow,
        }
    
    return _check_health()
