import logging
from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import exchange_code_for_token
from app.auth import get_github_user_data
from app.database import get_db
from app.database.models import User
from app.dependencies import config
from app.dependencies import current_user
from app.schemas import CaseStatusUpdate
from app.schemas import Page
from app.schemas import Study
from app.schemas import StudyCreate
from app.schemas import StudyResponse
from app.schemas import UserResponse
from app.services import study_service
from app.services.user_service import get_all_users
from app.services.user_service import get_or_create_user
from app.settings import Settings

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "user": {"username": user.username, "avatar_url": user.avatar_url} if user else None,
        "login_url": str(request.url_for("auth_login")),
        "logout_url": str(request.url_for("auth_logout")),
    }


@router.get("/api/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/auth/login")
async def auth_login(
    request: Request,
    config: Annotated[Settings, Depends(config)],
) -> RedirectResponse:
    if config.dummy_auth:
        return RedirectResponse(
            request.url_for("auth_callback").include_query_params(code="dummy-code")
        )

    return RedirectResponse(config.login_url)


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Annotated[str, Query],
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    response = RedirectResponse(request.url_for("home"))

    if access_token := await exchange_code_for_token(code, config):
        response.set_cookie(key="access_token", value=access_token)

        if not config.dummy_auth:
            github_user = await get_github_user_data(access_token)
            await get_or_create_user(
                db,
                github_id=github_user.id,
                username=github_user.login,
                avatar_url=github_user.avatar_url,
            )

    return response


@router.get("/auth/logout")
async def auth_logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(request.url_for("home"))
    response.delete_cookie(key="access_token")
    return response


# --- User API Endpoints ---


@router.get("/api/users")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[UserResponse]:
    """List all known users."""
    users = await get_all_users(db)
    items = [UserResponse(id=u.id, username=u.username, avatar_url=u.avatar_url) for u in users]
    return Page(items=items, total=len(items))


# --- Study API Endpoints ---


@router.get("/api/studies")
async def list_studies(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[Study]:
    """List all studies."""
    studies = await study_service.get_all_studies(db)
    return Page(items=studies, total=len(studies))


@router.post("/api/studies", status_code=status.HTTP_201_CREATED)
async def create_study(
    payload: StudyCreate,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Register a new study with its cases."""
    study = await study_service.create_study(db, payload, pushed_by_id=user.id if user else None)
    log.info(f"Created study {study.id} with {len(study.cases)} cases")
    return study


@router.get("/api/studies/{study_id}")
async def get_study(
    study_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Fetch a study by ID (raw format)."""
    study = await study_service.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.put("/api/studies/{study_id}")
async def update_study(
    study_id: str,
    payload: StudyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Update an existing study, upserting cases."""
    study = await study_service.update_study(db, study_id, payload)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    log.info(f"Updated study {study.id} with {len(study.cases)} cases")
    return study


@router.delete("/api/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(
    study_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a study and all its cases."""
    deleted = await study_service.delete_study(db, study_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Study not found")
    log.info(f"Deleted study {study_id}")


@router.get("/api/studies/{study_id}/detail")
async def get_study_detail(
    study_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudyResponse:
    """Fetch a study in UI-friendly format."""
    study = await study_service.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyResponse.from_study(study)


@router.patch("/api/studies/{study_id}/cases/{case_id}")
async def update_case_status(
    study_id: str,
    case_id: str,
    update: CaseStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update the status of a case within a study."""
    case = await study_service.update_case_status(db, study_id, case_id, update)
    if not case:
        raise HTTPException(status_code=404, detail="Study or case not found")
    log.info(f"Updated case {case_id} in study {study_id} to {update.status}")
    return {"status": "ok", "case": case}
