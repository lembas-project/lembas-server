"""Tests for the schema registry API endpoints."""

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.dependencies import current_user
from app.schemas import HandlerSchemaPayload
from app.schemas import StudyCreatePayload
from app.services.study_service import create_study

SAMPLE_SCHEMA = {
    "title": "PlaningPlateCase",
    "description": "Planing flat plate hydrodynamics case",
    "inputs": {
        "properties": {
            "froude_num": {"type": "number"},
            "angle_of_attack": {"type": "number"},
        }
    },
    "results": {
        "properties": {
            "lift": {"type": "number"},
            "drag": {"type": "number"},
        }
    },
    "steps": [],
}


async def test_list_schemas_empty(client: AsyncClient) -> None:
    response = await client.get("/api/schemas")
    assert response.status_code == 200
    assert response.json() == []


async def test_schema_registered_with_study(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=5000001, username="schemauser", avatar_url="")

    async def override() -> User:
        return user

    app.dependency_overrides[current_user] = override
    try:
        payload = {
            "name": "schema-test-study",
            "handlers": [
                {
                    "fingerprint": "abcdef0123456789",
                    "name": "PlaningPlateCase",
                    "schema": SAMPLE_SCHEMA,
                }
            ],
            "cases": [
                {"id": "case001", "handler_fqn": "plugin.PlaningPlateCase", "inputs": {}}
            ],
        }
        resp = await client.post("/api/studies", json=payload)
        assert resp.status_code == 201
    finally:
        app.dependency_overrides.pop(current_user)

    # Schema should now appear in the registry
    response = await client.get("/api/schemas")
    assert response.status_code == 200
    schemas = response.json()
    assert len(schemas) == 1
    assert schemas[0]["fingerprint"] == "abcdef0123456789"
    assert schemas[0]["name"] == "PlaningPlateCase"
    assert schemas[0]["schema"]["title"] == "PlaningPlateCase"
    assert len(schemas[0]["used_by"]) == 1
    assert schemas[0]["used_by"][0]["study_name"] == "schema-test-study"


async def test_get_schema_by_fingerprint(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=5000002, username="schemauser2", avatar_url="")
    payload = StudyCreatePayload(
        name="fingerprint-test",
        handlers=[
            HandlerSchemaPayload(
                fingerprint="fedcba9876543210",
                name="MyHandler",
                schema={"title": "MyHandler", "inputs": {}, "results": {}},
            )
        ],
        cases=[],
    )
    await create_study(db, payload, pushed_by_id=user.id)

    response = await client.get("/api/schemas/fedcba9876543210")
    assert response.status_code == 200
    data = response.json()
    assert data["fingerprint"] == "fedcba9876543210"
    assert data["name"] == "MyHandler"


async def test_get_schema_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/schemas/nonexistent")
    assert response.status_code == 404


async def test_schemas_deduplicated_across_studies(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    """Same fingerprint pushed with two studies should appear once."""
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=5000003, username="schemauser3", avatar_url="")
    handler = HandlerSchemaPayload(
        fingerprint="dedup1234567890a",
        name="SharedHandler",
        schema={"title": "SharedHandler", "inputs": {}, "results": {}},
    )

    async def override() -> User:
        return user

    app.dependency_overrides[current_user] = override
    try:
        for name in ("study-a", "study-b"):
            resp = await client.post(
                "/api/studies",
                json={
                    "name": name,
                    "handlers": [
                        {
                            "fingerprint": handler.fingerprint,
                            "name": handler.name,
                            "schema": handler.schema_,
                        }
                    ],
                    "cases": [],
                },
            )
            assert resp.status_code == 201
    finally:
        app.dependency_overrides.pop(current_user)

    response = await client.get("/api/schemas")
    fingerprints = [s["fingerprint"] for s in response.json()]
    assert fingerprints.count("dedup1234567890a") == 1

    schema = next(s for s in response.json() if s["fingerprint"] == "dedup1234567890a")
    assert len(schema["used_by"]) == 2
