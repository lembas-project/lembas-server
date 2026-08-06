"""Database initialization and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base as Base
from app.settings import Settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(settings: Settings, *, create_tables: bool = False) -> None:
    """Initialize the database engine and optionally create tables.

    Args:
        settings: Application settings containing database_url.
        create_tables: If True, create all tables directly (for testing).
            In production, use Alembic migrations instead.
    """
    global _engine, _session_factory

    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(settings.database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    if create_tables:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close the database engine."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database first.")
    async with _session_factory() as session:
        yield session


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for use outside FastAPI)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database first.")
    async with _session_factory() as session:
        yield session
