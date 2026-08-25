
from fastapi import FastAPI
from httpx import AsyncClient

from app.database.models import User
from app.dependencies import current_user


async def test_get_home_anonymous(client: AsyncClient, base_url: str) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"] is None
    assert data["login_url"] == f"{base_url}/auth/login"
    assert data["logout_url"] == f"{base_url}/auth/logout"


async def test_get_home_logged_in(
    app: FastAPI, client: AsyncClient, base_url: str
) -> None:
    dummy_user = User(id="test-uuid", github_id="12345", username="dummy", avatar_url="")

    async def override_current_user() -> User:
        return dummy_user

    app.dependency_overrides[current_user] = override_current_user
    try:
        client.cookies.set("access_token", "dummy-token")
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["user"]["username"] == "dummy"
        assert data["login_url"] == f"{base_url}/auth/login"
        assert data["logout_url"] == f"{base_url}/auth/logout"
    finally:
        app.dependency_overrides.pop(current_user)
