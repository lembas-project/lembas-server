from unittest.mock import Mock

from httpx import AsyncClient


async def test_get_health(client: AsyncClient) -> None:
    response = await client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


async def test_auth_callback_success(client: AsyncClient, mocker: Mock, base_url: str) -> None:
    mock = mocker.patch("app.routes.exchange_code_for_token", return_value="valid-access-token")

    response = await client.get(
        "/auth/callback", params={"code": "valid-code"}, follow_redirects=False
    )

    mock.assert_called_once()

    assert response.status_code == 307
    assert response.headers["Location"] == f"{base_url}/"

    assert response.cookies.get("access_token") == "valid-access-token"


async def test_auth_callback_redirect_on_failure(
    client: AsyncClient, mocker: Mock, base_url: str
) -> None:
    mock = mocker.patch("app.routes.exchange_code_for_token", return_value=None)

    response = await client.get(
        "/auth/callback", params={"code": "bad-code"}, follow_redirects=False
    )

    mock.assert_called_once()

    assert response.status_code == 307
    assert response.headers["Location"] == f"{base_url}/"

    assert response.cookies.get("access_token") is None


async def test_create_study(client: AsyncClient) -> None:
    payload = {
        "name": "test-study",
        "project_id": 1,
        "description": "A test study",
        "tags": ["test"],
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
    response = await client.post("/api/studies", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "test-study"
    assert data["project_id"] == 1
    assert len(data["cases"]) == 2
    assert "abc123" in data["cases"]
    assert data["cases"]["abc123"]["status"] == "pending"

    return data["id"]


async def test_get_study(client: AsyncClient) -> None:
    # First create a study
    payload = {
        "name": "fetch-test",
        "project_id": 1,
        "cases": [{"case_id": "xyz789", "handler_fqn": "test.Case", "inputs": {}}],
    }
    create_response = await client.post("/api/studies", json=payload)
    study_id = create_response.json()["id"]

    # Then fetch it
    response = await client.get(f"/api/studies/{study_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == study_id
    assert data["name"] == "fetch-test"


async def test_get_study_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/studies/nonexistent-id")
    assert response.status_code == 404


async def test_update_case_status(client: AsyncClient) -> None:
    # Create a study
    payload = {
        "name": "status-test",
        "project_id": 1,
        "cases": [{"case_id": "case001", "handler_fqn": "test.Case", "inputs": {}}],
    }
    create_response = await client.post("/api/studies", json=payload)
    study_id = create_response.json()["id"]

    # Update case to running
    response = await client.patch(
        f"/api/studies/{study_id}/cases/case001",
        json={"status": "running"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "running"
    assert data["case"]["started_at"] is not None

    # Update case to complete
    response = await client.patch(
        f"/api/studies/{study_id}/cases/case001",
        json={"status": "complete"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["status"] == "complete"
    assert data["case"]["completed_at"] is not None


async def test_get_project_studies(client: AsyncClient) -> None:
    # Create a couple of studies in project 2
    await client.post(
        "/api/studies",
        json={"name": "study-a", "project_id": 2, "cases": []},
    )
    await client.post(
        "/api/studies",
        json={"name": "study-b", "project_id": 2, "cases": []},
    )

    response = await client.get("/api/projects/2/studies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [s["name"] for s in data]
    assert "study-a" in names
    assert "study-b" in names
