"""Tests for the Study API endpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient

from app.database.models import User
from app.dependencies import current_user

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

FAKE_USER = User(
    id="00000000-0000-0000-0000-000000000001",
    github_id="99999",
    username="testuser",
    avatar_url="",
)
OTHER_USER = User(
    id="00000000-0000-0000-0000-000000000002",
    github_id="88888",
    username="otheruser",
    avatar_url="",
)


@asynccontextmanager
async def as_user(app: FastAPI, user: User | None) -> AsyncIterator[None]:
    """Context manager to override current_user for a block of code."""

    async def override() -> User | None:
        return user

    app.dependency_overrides[current_user] = override
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_user)


async def test_list_studies(client: AsyncClient) -> None:
    # Create two studies
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
    # limit and offset are null until pagination is implemented
    assert data["limit"] is None
    assert data["offset"] is None

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


async def test_get_study(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "fetch-test",
            "cases": [{"id": "xyz789", "handler_fqn": "test.Case", "inputs": {}}],
        },
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


async def test_update_study(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post(
            "/api/studies",
            json={
                "name": "update-test",
                "cases": [{"id": "case-a", "handler_fqn": "test.Case", "inputs": {"x": 1}}],
            },
        )
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

        update_payload = {
            "name": "update-test-renamed",
            "cases": [
                {"id": "case-a", "handler_fqn": "test.Case", "inputs": {"x": 2}},
                {"id": "case-b", "handler_fqn": "test.Case", "inputs": {"x": 3}},
            ],
        }
        response = await client.put(f"/api/studies/{study_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "update-test-renamed"
        assert len(data["cases"]) == 2
        assert "case-b" in data["cases"]
        assert data["cases"]["case-a"]["inputs"] == {"x": 2}


async def test_update_study_forbidden_unauthenticated(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    # Unauthenticated (no user)
    async with as_user(app, None):
        response = await client.put(f"/api/studies/{study_id}", json={"name": "x", "cases": []})
        assert response.status_code == 403


async def test_update_study_forbidden_wrong_user(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, OTHER_USER):
        response = await client.put(f"/api/studies/{study_id}", json={"name": "x", "cases": []})
        assert response.status_code == 403


async def test_update_study_not_found(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        response = await client.put("/api/studies/nonexistent-id", json={"name": "x", "cases": []})
        assert response.status_code == 404


async def test_delete_study(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post("/api/studies", json={"name": "delete-test", "cases": []})
        assert create_resp.status_code == 201
        study_id = create_resp.json()["id"]

        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 204

    response = await client.get(f"/api/studies/{study_id}")
    assert response.status_code == 404


async def test_delete_study_forbidden_unauthenticated(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, None):
        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 403


async def test_delete_study_forbidden_wrong_user(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        create_resp = await client.post("/api/studies", json={"name": "owned", "cases": []})
        study_id = create_resp.json()["id"]

    async with as_user(app, OTHER_USER):
        response = await client.delete(f"/api/studies/{study_id}")
        assert response.status_code == 403


async def test_delete_study_not_found(app: FastAPI, client: AsyncClient) -> None:
    async with as_user(app, FAKE_USER):
        response = await client.delete("/api/studies/nonexistent-id")
        assert response.status_code == 404


async def test_get_study_detail(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "detail-test",
            "cases": [{"id": "c1", "handler_fqn": "test.Case", "inputs": {"param": "value"}}],
        },
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


async def test_update_case_status_to_running(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "status-test",
            "cases": [{"id": "case001", "handler_fqn": "test.Case", "inputs": {}}],
        },
    )
    assert create_resp.status_code == 201
    study_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/studies/{study_id}/cases/case001",
        json={"status": "running"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "running"
    assert data["case"]["started_at"] is not None


async def test_update_case_status_to_complete(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "complete-test",
            "cases": [{"id": "case002", "handler_fqn": "test.Case", "inputs": {}}],
        },
    )
    assert create_resp.status_code == 201
    study_id = create_resp.json()["id"]

    # running → complete
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


async def test_update_case_status_failed_with_error(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "fail-test",
            "cases": [{"id": "case003", "handler_fqn": "test.Case", "inputs": {}}],
        },
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
