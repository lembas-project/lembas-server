"""Tests for the Study API endpoints."""

from httpx import AsyncClient

STUDY_PAYLOAD = {
    "name": "test-study",
    "description": "A test study",
    "tags": ["test", "unit"],
    "plugins_declared": ["lembas-planing-plate"],
    "cases": [
        {
            "case_id": "abc123",
            "handler_fqn": "lembas_planing_plate.PlaningPlateCase",
            "inputs": {"froude_num": 0.5, "angle_of_attack": 5.0},
        },
        {
            "case_id": "def456",
            "handler_fqn": "lembas_planing_plate.PlaningPlateCase",
            "inputs": {"froude_num": 0.8, "angle_of_attack": 10.0},
        },
    ],
}


async def test_create_study(client: AsyncClient) -> None:
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
            "cases": [{"case_id": "xyz789", "handler_fqn": "test.Case", "inputs": {}}],
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


async def test_update_study(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "update-test",
            "cases": [{"case_id": "case-a", "handler_fqn": "test.Case", "inputs": {"x": 1}}],
        },
    )
    assert create_resp.status_code == 201
    study_id = create_resp.json()["id"]

    # Update study: rename, add a new case
    update_payload = {
        "name": "update-test-renamed",
        "cases": [
            {"case_id": "case-a", "handler_fqn": "test.Case", "inputs": {"x": 2}},
            {"case_id": "case-b", "handler_fqn": "test.Case", "inputs": {"x": 3}},
        ],
    }
    response = await client.put(f"/api/studies/{study_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "update-test-renamed"
    assert len(data["cases"]) == 2
    assert "case-b" in data["cases"]
    # Existing case inputs should be updated
    assert data["cases"]["case-a"]["inputs"] == {"x": 2}


async def test_update_study_not_found(client: AsyncClient) -> None:
    response = await client.put("/api/studies/nonexistent-id", json={"name": "x", "cases": []})
    assert response.status_code == 404


async def test_delete_study(client: AsyncClient) -> None:
    create_resp = await client.post("/api/studies", json={"name": "delete-test", "cases": []})
    assert create_resp.status_code == 201
    study_id = create_resp.json()["id"]

    response = await client.delete(f"/api/studies/{study_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/studies/{study_id}")
    assert response.status_code == 404


async def test_delete_study_not_found(client: AsyncClient) -> None:
    response = await client.delete("/api/studies/nonexistent-id")
    assert response.status_code == 404


async def test_get_study_detail(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/studies",
        json={
            "name": "detail-test",
            "cases": [{"case_id": "c1", "handler_fqn": "test.Case", "inputs": {"param": "value"}}],
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
            "cases": [{"case_id": "case001", "handler_fqn": "test.Case", "inputs": {}}],
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
            "cases": [{"case_id": "case002", "handler_fqn": "test.Case", "inputs": {}}],
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
            "cases": [{"case_id": "case003", "handler_fqn": "test.Case", "inputs": {}}],
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


async def test_study_with_handler_schemas(client: AsyncClient) -> None:
    """Test that handler schemas are stored and returned with the study."""
    payload = {
        "name": "schema-test",
        "handlers": [
            {
                "name": "PlaningPlateCase",
                "schema": {
                    "title": "PlaningPlateCase",
                    "inputs": {"properties": {"froude_num": {"type": "number"}}},
                    "results": {"properties": {"lift": {"type": "number"}}},
                    "steps": [],
                },
                "schema_fingerprint": "abcdef012345",
            }
        ],
        "cases": [{"case_id": "h1", "handler_fqn": "test.PlaningPlateCase", "inputs": {}}],
    }
    response = await client.post("/api/studies", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "abcdef012345" in data["handlers"]
    assert data["handlers"]["abcdef012345"]["title"] == "PlaningPlateCase"
