"""Tests for the API token endpoints and Bearer token authentication."""

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.dependencies import current_user


async def test_create_token_unauthenticated(client: AsyncClient) -> None:
    response = await client.post("/api/tokens", json={})
    assert response.status_code == 401


async def test_create_token(app: FastAPI, client: AsyncClient, db: AsyncSession) -> None:
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=3000001, username="tokenuser", avatar_url="")

    async def override() -> User:
        return user

    app.dependency_overrides[current_user] = override
    try:
        response = await client.post("/api/tokens", json={"name": "ci-token"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ci-token"
        assert data["token"].startswith("lb_v1_")
        assert len(data["token"]) == 70  # lb_v1_ (6) + 64 hex chars
        assert "id" in data
        assert "created_at" in data
        # token must not be re-exposed on subsequent listing
        raw_token = data["token"]
    finally:
        app.dependency_overrides.pop(current_user)

    # Token value must not appear in listing
    app.dependency_overrides[current_user] = override
    try:
        list_resp = await client.get("/api/tokens")
        assert list_resp.status_code == 200
        tokens = list_resp.json()
        assert any(t["name"] == "ci-token" for t in tokens)
        assert all("token" not in t for t in tokens)
    finally:
        app.dependency_overrides.pop(current_user)

    return raw_token


async def test_bearer_token_authenticates_user(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    from app.services.token_service import create_token
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=3000002, username="beareruser", avatar_url="")
    token = await create_token(db, user, name="test")

    # Use the token via Authorization header — no dependency override needed
    response = await client.get(
        "/api/tokens",
        headers={"Authorization": f"Bearer {token.token}"},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert any(t["id"] == token.id for t in tokens)


async def test_bearer_token_invalid(client: AsyncClient) -> None:
    response = await client.get(
        "/api/studies",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    # Studies list is public, but this tests the dependency doesn't crash on bad token
    assert response.status_code == 200


async def test_delete_token(app: FastAPI, client: AsyncClient, db: AsyncSession) -> None:
    from app.services.token_service import create_token
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=3000003, username="deleteuser", avatar_url="")
    token = await create_token(db, user, name="to-delete")

    async def override() -> User:
        return user

    app.dependency_overrides[current_user] = override
    try:
        response = await client.delete(f"/api/tokens/{token.id}")
        assert response.status_code == 204

        # Confirm it's gone
        list_resp = await client.get("/api/tokens")
        assert not any(t["id"] == token.id for t in list_resp.json())
    finally:
        app.dependency_overrides.pop(current_user)


async def test_delete_token_not_found(app: FastAPI, client: AsyncClient, db: AsyncSession) -> None:
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=3000004, username="notfounduser", avatar_url="")

    async def override() -> User:
        return user

    app.dependency_overrides[current_user] = override
    try:
        response = await client.delete("/api/tokens/nonexistent-id")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(current_user)


async def test_revoke_current_token(client: AsyncClient, db: AsyncSession) -> None:
    """DELETE /api/tokens/current revokes the token used in the request."""
    from app.services.token_service import create_token
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=3000005, username="revokeuser", avatar_url="")
    token = await create_token(db, user, name="to-revoke")

    response = await client.delete(
        "/api/tokens/current",
        headers={"Authorization": f"Bearer {token.token}"},
    )
    assert response.status_code == 204

    # Token should no longer authenticate
    auth_resp = await client.get(
        "/api/tokens",
        headers={"Authorization": f"Bearer {token.token}"},
    )
    assert auth_resp.status_code == 401


async def test_revoke_current_token_unauthenticated(client: AsyncClient) -> None:
    response = await client.delete("/api/tokens/current")
    assert response.status_code == 401
