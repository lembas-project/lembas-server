from collections.abc import AsyncIterator
from collections.abc import Callable

import httpx
import pytest
import sqlalchemy
from fastapi import FastAPI
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import close_database
from app.database import get_db_context
from app.database import get_engine
from app.database import init_database
from app.database.models import Base
from app.main import create_app
from app.settings import Settings

ClientFactory = Callable[[], httpx.AsyncClient]


@pytest.fixture(scope="session")
async def app() -> AsyncIterator[FastAPI]:
    config = Settings(
        client_id="test-client-id",
        client_secret="test-client-secret",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    app = create_app(config=config)
    await init_database(config)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield app
    await close_database()


@pytest.fixture
async def db(app: FastAPI) -> AsyncIterator[AsyncSession]:
    """Provide a database session for tests."""
    async with get_db_context() as session:
        yield session


@pytest.fixture(scope="session")
def base_url() -> str:
    return "http://test"


@pytest.fixture(scope="session")
async def client_factory(app: FastAPI, base_url: str) -> AsyncIterator[ClientFactory]:
    """A factory to construct an HTTPX AsyncClient."""
    clients = []

    def create_client() -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=app)  # type: ignore
        client_ = httpx.AsyncClient(transport=transport, base_url=base_url)
        clients.append(client_)
        return client_

    yield create_client

    for client_ in clients:
        await client_.aclose()


@pytest.fixture(scope="function")
def client(client_factory: ClientFactory) -> httpx.AsyncClient:
    """An HTTP session."""
    return client_factory()


@pytest.fixture
def alembic_engine() -> Engine:
    """Synchronous SQLite engine for pytest-alembic migration tests."""
    return sqlalchemy.create_engine("sqlite://")
