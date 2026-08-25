"""Tests for the Study API endpoints."""

from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.dependencies import current_user
from app.services.user_service import get_or_create_user

STUDY_PAYLOAD = {
    "name": "test-study",
    "description": "A test study",
    "tags": ["test", "unit"],
    "plugins_declared": ["lembas-planing-plate"],
    "cases": [
        {
            "id": "abc123",
            "handler_fqn": "lembas_planing_plate.PlaningPlateCase",
            "inputs": {"froude_num": 0.5, "angle_of_attack": 5.0},
        },
        {
            "id": "def456",
            "handler_fqn": "lembas_planing_plate.PlaningPlateCase",
            "inputs": {"froude_num": 0.8, "angle_of_attack": 10.0},
        },
    ],
}


@pytest.fixture
async def fake_user(db: AsyncSession) -> User:
    return await get_or_create_user(db, github_id=2000001, username="testuser", avatar_url="")


@pytest.fixture
async def other_user(db: AsyncSession) -> User:
    return await get_or_create_user(db, github_id=2000002, username="otheruser", avatar_url="")


def _case(case_id: str, **inputs: object) -> dict:
    return {"id": case_id, "handler_fqn": "test.Case", "inputs": dict(inputs)}


def as_user(app: FastAPI, user: User | None) -> AbstractAsyncContextManager[None]:
    """Context manager to override current_user for a block of code."""
    return _as_user_ctx(app, user)


@asynccontextmanager
async def _as_user_ctx(app: FastAPI, user: User | None) -> AsyncGenerator[None, None]:
    async def override() -> User | None:
        return user

    app.dependency_overrides[current_user] = override
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_user)


async def test_create_study(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        response = await client.post("/api/studies", json=STUDY_PAYLOAD)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "test-study"
        assert data["description"] == "A test study"
        assert data["tags"] == ["test", "unit"]
        assert len(data["cases"]) == 2
        assert "abc123" in data["cases"]
        assert "def456" in data["cases"]
        assert data["cases"]["abc123"]["status"] == "pending"
        assert data["cases"]["abc123"]["inputs"] == {"froude_num": 0.5, "angle_of_attack": 5.0}
        assert "id" in data
        assert "created_at" in data


async def test_create_study_unauthenticated(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, None):
        response = await client.post("/api/studies", json={"name": "anon", "cases": []})
        assert response.status_code == 401


async def test_list_studies(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        for name in ("list-study-a", "list-study-b"):
            resp = await client.post("/api/studies", json={"name": name, "cases": []})
            assert resp.status_code == 201

    response = await client.get("/api/studies")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    names = [s["name"] for s in data["items"]]
    assert "list-study-a" in names
    assert "list-study-b" in names
    assert data["total"] == len(data["items"])


async def test_list_studies_empty_pagination_fields(client: AsyncClient) -> None:
    response = await client.get("/api/studies")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] is None
    assert data["offset"] is None


async def test_get_study(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "fetch-test", "cases": [_case("xyz789")]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

    response = await client.get(f"/api/studies/{study_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == study_id
    assert data["name"] == "fetch-test"
    assert "xyz789" in data["cases"]


async def test_get_study_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/studies/nonexistent-id")
    assert response.status_code == 404


async def test_update_study(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "update-test", "cases": [_case("case-a", x=1)]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

        response = await client.put(f"/api/studies/{study_id}", json={
            "name": "update-test-renamed",
            "cases": [
                {"id": "case-a", "handler_fqn": "test.Case", "inputs": {"x": 2}},
                {"id": "case-b", "handler_fqn": "test.Case", "inputs": {"x": 3}},
            ],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "update-test-renamed"
        assert len(data["cases"]) == 2
        assert "case-b" in data["cases"]
        assert data["cases"]["case-a"]["inputs"] == {"x": 2}


async def test_update_study_unauthenticated(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, None):
        response = await client.put(f"/api/studies/{study_id}", json={"name": "x", "cases": []})
        assert response.status_code == 403


async def test_update_study_forbidden_wrong_user(
    app: FastAPI, client: AsyncClient, fake_user: User, other_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, other_user):
        response = await client.put(f"/api/studies/{study_id}", json={"name": "x", "cases": []})
        assert response.status_code == 403


async def test_update_study_not_found(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        response = await client.put("/api/studies/nonexistent-id", json={"name": "x", "cases": []})
        assert response.status_code == 404


async def test_delete_study(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post("/api/studies", json={"name": "delete-test", "cases": []})
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 204

    response = await client.get(f"/api/studies/{study_id}")
    assert response.status_code == 404


async def test_delete_study_unauthenticated(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, None):
        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 403


async def test_delete_study_forbidden_wrong_user(
    app: FastAPI, client: AsyncClient, fake_user: User, other_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, other_user):
        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 403


async def test_delete_study_not_found(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        response = await client.delete("/api/studies/nonexistent-id")
        assert response.status_code == 404


async def test_get_study_detail(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "detail-test", "cases": [_case("c1", param="value")]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

    response = await client.get(f"/api/studies/{study_id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["study_id"] == study_id
    assert data["meta"]["name"] == "detail-test"
    assert len(data["runs"]) == 1
    assert data["runs"][0]["case_id"] == "c1"
    assert data["runs"][0]["status"] == "pending"


async def test_update_case_status_to_running(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "status-test", "cases": [_case("case001")]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/studies/{study_id}/cases/case001", json={"status": "running"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "running"
    assert data["case"]["started_at"] is not None


async def test_update_case_status_to_complete(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "complete-test", "cases": [_case("case002")]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

    await client.patch(f"/api/studies/{study_id}/cases/case002", json={"status": "running"})
    response = await client.patch(
        f"/api/studies/{study_id}/cases/case002",
        json={"status": "complete", "duration_seconds": 1.5, "results": {"lift": 42.0}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "complete"
    assert data["case"]["completed_at"] is not None
    assert data["case"]["duration_seconds"] == 1.5
    assert data["case"]["results"] == {"lift": 42.0}


async def test_update_case_status_failed_with_error(
    app: FastAPI, client: AsyncClient, fake_user: User
) -> None:
    async with as_user(app, fake_user):
        create_resp = await client.post(
            "/api/studies",
            json={"name": "fail-test", "cases": [_case("case003")]},
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/studies/{study_id}/cases/case003",
        json={"status": "failed", "error_message": "Something went wrong"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "failed"
    assert data["case"]["error_message"] == "Something went wrong"


async def test_update_case_status_not_found(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/studies/nonexistent-id/cases/case001",
        json={"status": "running"},
    )
    assert response.status_code == 404
