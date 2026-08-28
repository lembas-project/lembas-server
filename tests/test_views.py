from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import CaseRunCreate
from app.schemas import StudyCreatePayload
from app.services.study_service import create_study


async def test_root_redirects_to_studies(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/studies"


async def test_studies_gallery_renders(client: AsyncClient) -> None:
    response = await client.get("/studies", follow_redirects=True)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_study_detail_renders(app: FastAPI, client: AsyncClient, db: AsyncSession) -> None:
    """Study detail page must render and include correct case row URLs."""
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=4000001, username="uiuser", avatar_url="")
    payload = StudyCreatePayload(
        name="ui-test-study",
        cases=[],
    )
    study = await create_study(db, payload, pushed_by_id=user.id)

    response = await client.get(f"/studies/{study.id}")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ui-test-study" in response.text


async def test_case_detail_partial_has_correct_url(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    """Case rows must include the study_id so the detail panel URL is not empty."""
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=4000002, username="uiuser2", avatar_url="")
    payload = StudyCreatePayload(
        name="url-test-study",
        cases=[
            CaseRunCreate(id="abc123", handler_fqn="test.Case", inputs={"x": 1.0}),
        ],
    )
    study = await create_study(db, payload, pushed_by_id=user.id)

    response = await client.get(f"/studies/{study.id}")
    assert response.status_code == 200
    # The case row hx-get URL must contain the study_id — not a double slash
    assert f"/studies/{study.id}/cases/abc123" in response.text
    assert "/studies//cases/" not in response.text


async def test_case_detail_partial_renders(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    """GET /studies/{id}/cases/{case_id} returns the case detail partial."""
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=4000003, username="uiuser3", avatar_url="")
    payload = StudyCreatePayload(
        name="detail-partial-study",
        cases=[
            CaseRunCreate(id="def456", handler_fqn="test.Case", inputs={"y": 2.0}),
        ],
    )
    study = await create_study(db, payload, pushed_by_id=user.id)

    response = await client.get(f"/studies/{study.id}/cases/def456", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "def456" in response.text
    assert "test.Case" in response.text


async def test_case_detail_deep_link(
    app: FastAPI, client: AsyncClient, db: AsyncSession
) -> None:
    """Direct navigation to /studies/{id}/cases/{case_id} renders full study page."""
    from app.services.user_service import get_or_create_user

    user = await get_or_create_user(db, github_id=4000004, username="deeplink", avatar_url="")
    payload = StudyCreatePayload(
        name="deep-link-study",
        cases=[CaseRunCreate(id="deep123", handler_fqn="test.Case", inputs={})],
    )
    study = await create_study(db, payload, pushed_by_id=user.id)

    # No HX-Request header — direct navigation
    response = await client.get(f"/studies/{study.id}/cases/deep123")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Full page — contains study name and the selected_case_id JS
    assert "deep-link-study" in response.text
    assert "deep123" in response.text


async def test_study_detail_404(client: AsyncClient) -> None:
    response = await client.get("/studies/nonexistent-id")
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text
