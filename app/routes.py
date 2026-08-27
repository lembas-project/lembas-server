import logging
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import exchange_code_for_token
from app.auth import get_github_user_data
from app.auth import poll_device_token
from app.auth import request_device_code
from app.database import get_db
from app.database.models import User
from app.dependencies import config
from app.dependencies import current_user
from app.dependencies import get_templates
from app.schemas import CaseStatusUpdatePayload
from app.schemas import DeviceFlowResponse
from app.schemas import DevicePendingResponse
from app.schemas import DeviceTokenRequest
from app.schemas import DeviceTokenResponse
from app.schemas import HealthResponse
from app.schemas import Page
from app.schemas import Study
from app.schemas import StudyCreatePayload
from app.schemas import StudyResponse
from app.schemas import TokenCreatePayload
from app.schemas import TokenMetadata
from app.schemas import TokenResponse
from app.schemas import UserResponse
from app.services import study_service
from app.services.token_service import create_token
from app.services.token_service import delete_token
from app.services.token_service import delete_token_by_value
from app.services.token_service import list_tokens
from app.services.user_service import get_all_users
from app.services.user_service import get_or_create_user
from app.settings import Settings

log = logging.getLogger(__name__)

# Routes excluded from API docs (non-REST: redirects, OAuth flow, HTML pages)
hidden_router = APIRouter(include_in_schema=False)

# REST API routes — all mounted under /api in main.py
api_router = APIRouter()


# --- Hidden routes ---


@hidden_router.get("/auth/login")
async def auth_login(
    request: Request,
    config: Annotated[Settings, Depends(config)],
) -> RedirectResponse:
    if config.dummy_auth:
        return RedirectResponse(
            request.url_for("auth_callback").include_query_params(code="dummy-code")
        )
    return RedirectResponse(config.login_url)


@hidden_router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Annotated[str, Query],
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    response = RedirectResponse(request.url_for("root"))

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


@hidden_router.get("/auth/logout")
async def auth_logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(request.url_for("root"))
    response.delete_cookie(key="access_token")
    return response


# --- API routes ---


@api_router.get("/healthz")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


# --- User API Endpoints ---


@api_router.get("/users")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[UserResponse]:
    """List all known users."""
    users = await get_all_users(db)
    items = [UserResponse(id=u.id, username=u.username, avatar_url=u.avatar_url) for u in users]
    return Page(items=items, total=len(items))


# --- Token API Endpoints ---


@api_router.get("/auth/device")
async def device_flow_start(
    config: Annotated[Settings, Depends(config)],
) -> DeviceFlowResponse:
    """Initiate a device authorization flow.

    Returns a user_code to display and verification_uri to open in the browser.
    Poll POST /api/auth/device/token with the device_code until approved.
    """
    result = await request_device_code(config)
    return DeviceFlowResponse(
        device_code=result.device_code,
        user_code=result.user_code,
        verification_uri=result.verification_uri,
        interval=result.interval,
        expires_in=result.expires_in,
    )


@api_router.post("/auth/device/token")
async def device_flow_token(
    payload: DeviceTokenRequest,
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> DeviceTokenResponse | DevicePendingResponse:
    """Poll for a completed device authorization.

    Returns 201 with the API token once approved, or 200 with a pending/slow_down
    error while waiting. The client should poll at the interval returned by
    GET /api/auth/device.
    """
    result = await poll_device_token(payload.device_code, config)

    if result.error in ("authorization_pending", "slow_down"):
        response.status_code = status.HTTP_200_OK
        return DevicePendingResponse(
            error=result.error,  # type: ignore[arg-type]
            interval=result.interval if result.error == "slow_down" else None,
        )

    if result.error or not result.access_token:
        raise HTTPException(status_code=400, detail=result.error or "Device flow failed")

    # Exchange GitHub token for a lembas API token
    github_user = await get_github_user_data(result.access_token)
    user = await get_or_create_user(
        db,
        github_id=github_user.id,
        username=github_user.login,
        avatar_url=github_user.avatar_url,
    )
    api_token, raw_token = await create_token(db, user, name=payload.token_name or "cli")
    response.status_code = status.HTTP_201_CREATED
    return DeviceTokenResponse(token=raw_token, token_name=api_token.name)


@api_router.post("/tokens", status_code=status.HTTP_201_CREATED)
async def create_api_token(
    payload: TokenCreatePayload,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Create a new API token for the authenticated user.

    The token value is only returned once — store it securely.
    Requires authentication via GitHub OAuth session.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    api_token, raw_token = await create_token(db, user, name=payload.name)
    return TokenResponse(
        id=api_token.id,
        name=api_token.name,
        token=raw_token,
        created_at=api_token.created_at,
    )


@api_router.get("/tokens")
async def list_api_tokens(
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TokenMetadata]:
    """List all API tokens for the authenticated user (no token values)."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    tokens = await list_tokens(db, user)
    return [
        TokenMetadata(
            id=t.id,
            name=t.name,
            created_at=t.created_at,
            last_used_at=t.last_used_at,
        )
        for t in tokens
    ]


_bearer = HTTPBearer(auto_error=False)


@api_router.delete("/tokens/current", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke the token used to authenticate this request (self-revocation for logout)."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    await delete_token_by_value(db, credentials.credentials)


@api_router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_token(
    token_id: str,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke an API token. Only the owning user can delete their own tokens."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    deleted = await delete_token(db, token_id, user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")


# --- Study API Endpoints ---


@api_router.get("/studies")
async def list_studies(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[Study]:
    """List all studies."""
    studies = await study_service.get_all_studies(db)
    return Page(items=studies, total=len(studies))


@api_router.post("/studies", status_code=status.HTTP_201_CREATED)
async def create_study(
    payload: StudyCreatePayload,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Register a new study with its cases. Requires authentication."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    study = await study_service.create_study(db, payload, pushed_by_id=user.id)
    log.info(f"Created study {study.id} with {len(study.cases)} cases")
    return study


@api_router.get("/studies/{study_id}")
async def get_study(
    study_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Fetch a study by ID."""
    study = await study_service.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@api_router.put("/studies/{study_id}")
async def update_study(
    study_id: str,
    payload: StudyCreatePayload,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Study:
    """Update an existing study, upserting cases."""
    owner_id = await study_service.get_study_owner_id(db, study_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Study not found")
    if not user or owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this study")
    updated = await study_service.update_study(db, study_id, payload)
    assert updated is not None
    log.info(f"Updated study {study_id} with {len(updated.cases)} cases")
    return updated


@api_router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(
    study_id: str,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a study and all its cases."""
    owner_id = await study_service.get_study_owner_id(db, study_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Study not found")
    if not user or owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this study")
    await study_service.delete_study(db, study_id)
    log.info(f"Deleted study {study_id}")


@api_router.get("/studies/{study_id}/detail")
async def get_study_detail(
    study_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudyResponse:
    """Fetch a study in UI-friendly format."""
    study = await study_service.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyResponse.from_study(study)


@api_router.patch("/studies/{study_id}/cases/{case_id}")
async def update_case_status(
    study_id: str,
    case_id: str,
    payload: CaseStatusUpdatePayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update the status of a case within a study."""
    case = await study_service.update_case_status(db, study_id, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Study or case not found")
    log.info(f"Updated case {case_id} in study {study_id} to {payload.status}")
    return {"status": "ok", "case": case}


# --- UI Routes ---

ui_router = APIRouter(include_in_schema=False)


def _input_keys(studies_or_cases: list) -> list[str]:
    """Extract sorted unique input parameter keys across all cases."""
    keys: set[str] = set()
    for item in studies_or_cases:
        inputs = item.inputs if hasattr(item, "inputs") else {}
        keys.update(inputs.keys())
    return sorted(keys)


def _result_keys(cases: list) -> list[str]:
    """Extract sorted unique result keys across all cases that have results."""
    keys: set[str] = set()
    for case in cases:
        results = case.results if hasattr(case, "results") else {}
        keys.update(results.keys())
    return sorted(keys)


def _html_404(request: Request, message: str = "Page not found") -> HTMLResponse:
    templates = get_templates(request)
    return templates.TemplateResponse(request, "404.html", {"message": message}, status_code=404)


@ui_router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("/studies")


@ui_router.get("/studies", response_class=HTMLResponse)
async def studies_gallery(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
) -> HTMLResponse:
    studies = await study_service.get_all_studies(db)
    return templates.TemplateResponse(
        request,
        "studies_gallery.html",
        {"studies": studies, "active_page": "studies"},
    )


@ui_router.get("/studies/{study_id}", response_class=HTMLResponse)
async def study_detail(
    study_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
) -> HTMLResponse:
    study = await study_service.get_study(db, study_id)
    if not study:
        return _html_404(request, "Study not found")
    cases = list(study.cases.values())
    return templates.TemplateResponse(
        request,
        "study.html",
        {
            "study": study,
            "cases": cases,
            "input_keys": _input_keys(cases),
            "result_keys": _result_keys(cases),
            "active_page": "studies",
        },
    )


@ui_router.get("/studies/{study_id}/cases", response_class=HTMLResponse)
async def study_cases_partial(
    study_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    status: str | None = None,
) -> HTMLResponse:
    """htmx partial: filtered case table rows."""
    study = await study_service.get_study(db, study_id)
    if not study:
        return _html_404(request, "Study not found")
    cases = list(study.cases.values())
    if status:
        cases = [c for c in cases if c.status == status]
    return templates.TemplateResponse(
        request,
        "partials/case_rows.html",
        {
            "study": study,
            "cases": cases,
            "input_keys": _input_keys(cases),
            "result_keys": _result_keys(cases),
        },
    )


@ui_router.get("/studies/{study_id}/cases/{case_id}", response_class=HTMLResponse)
async def case_detail_partial(
    study_id: str,
    case_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
) -> HTMLResponse:
    """htmx partial: case detail panel."""
    study = await study_service.get_study(db, study_id)
    if not study:
        return _html_404(request, "Study not found")
    case = study.cases.get(case_id)
    if not case:
        return _html_404(request, f"Case {case_id[:8]} not found")
    return templates.TemplateResponse(
        request,
        "partials/case_detail.html",
        {"case": case},
    )
