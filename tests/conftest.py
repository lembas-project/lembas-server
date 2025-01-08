from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app
from app.settings import Settings

ClientFactory = Callable[[], httpx.AsyncClient]


@pytest.fixture(scope="session")
def app() -> FastAPI:
    config = Settings(
        client_id="test-client-id",
        client_secret="test-client-secret",
    )
    return create_app(config=config)


@pytest.fixture(scope="session")
async def client_factory(app: FastAPI) -> AsyncIterator[ClientFactory]:
    """A factory to construct an HTTPX AsyncClient."""
    clients = []

    def create_client() -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=app)  # type: ignore
        client_ = httpx.AsyncClient(transport=transport, base_url="http://test")
        clients.append(client_)
        return client_

    yield create_client

    for client_ in clients:
        await client_.aclose()


@pytest.fixture(scope="function")
def client(client_factory: ClientFactory) -> httpx.AsyncClient:
    """An HTTP session."""
    return client_factory()
