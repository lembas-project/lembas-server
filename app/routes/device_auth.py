"""Device flow authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_github_user_data
from app.database import get_db
from app.dependencies import config, current_user
from app.models import User
from app.services.device_flow import (
    DeviceFlowError,
    authorize_device_code,
    create_device_code_record,
    get_device_code_by_user_code,
    poll_device_code,
)
from app.services.user_service import get_or_create_user
from app.settings import Settings
from app.templates import render_template

router = APIRouter(tags=["device-auth"])


class DeviceCodeRequest(BaseModel):
    token_name: str = "CLI Token"


class DeviceCodeResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class DeviceTokenRequest(BaseModel):
    device_code: str
    grant_type: str = "urn:ietf:params:oauth:grant-type:device_code"


class DeviceTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DeviceErrorResponse(BaseModel):
    error: str
    error_description: str


@router.post("/auth/device/code")
async def request_device_code(
    request: Request,
    body: DeviceCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceCodeResponse:
    """Initiate device flow authentication.

    CLI calls this to get a user code to display.
    """
    verification_uri = str(request.url_for("device_authorize_page"))

    record = await create_device_code_record(
        db,
        verification_uri=verification_uri,
        token_name=body.token_name,
    )

    expires_in = int((record.expires_at - record.created_at).total_seconds())

    return DeviceCodeResponse(
        device_code=record.device_code,
        user_code=record.user_code,
        verification_uri=verification_uri,
        verification_uri_complete=f"{verification_uri}?user_code={record.user_code}",
        expires_in=expires_in,
        interval=record.interval,
    )


@router.post("/auth/device/token")
async def poll_device_token(
    body: DeviceTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(config)],
) -> DeviceTokenResponse | DeviceErrorResponse:
    """Poll for device code authorization status.

    CLI calls this repeatedly until it gets a token.
    """
    try:
        token, expires_in = await poll_device_code(
            db,
            device_code=body.device_code,
            token_expiry_days=settings.token_default_expiry_days,
        )
        return DeviceTokenResponse(access_token=token, expires_in=expires_in)
    except DeviceFlowError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": e.error, "error_description": e.description},
        )


@router.get("/device", name="device_authorize_page", response_model=None)
async def device_authorize_page(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(config)],
    user_code: str | None = None,
) -> HTMLResponse | RedirectResponse:
    """Web page for user to enter device code."""
    if user is None:
        redirect_url = str(request.url)
        login_url = str(request.url_for("auth_login")) + f"?next={redirect_url}"
        return RedirectResponse(login_url)

    error = None
    device_code = None

    if user_code:
        device_code = await get_device_code_by_user_code(db, user_code)
        if not device_code:
            error = "Invalid or expired code"

    return render_template(
        "device.html",
        request=request,
        user=user,
        user_code=user_code or "",
        error=error,
        device_code=device_code,
    )


@router.post("/device/authorize", response_model=None)
async def authorize_device(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(config)],
    user_code: Annotated[str, Form()],
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Authorize a device code (user submits from web page)."""
    if user is None or access_token is None:
        return RedirectResponse(request.url_for("auth_login"))

    device_code = await get_device_code_by_user_code(db, user_code)
    if not device_code:
        return render_template(
            "device.html",
            request=request,
            user=user,
            user_code=user_code,
            error="Invalid or expired code",
        )

    if settings.dummy_auth:
        db_user = await get_or_create_user(
            db,
            github_id=1,
            username="dummy",
            name="Dummy User",
            avatar_url="",
        )
    else:
        github_user = await get_github_user_data(access_token)
        db_user = await get_or_create_user(
            db,
            github_id=github_user.id,
            username=github_user.login,
            name=github_user.name,
            avatar_url=github_user.avatar_url,
        )

    success = await authorize_device_code(db, user_code, db_user.id)

    if success:
        return render_template("device_success.html", request=request, user=user)
    else:
        return render_template(
            "device.html",
            request=request,
            user=user,
            user_code=user_code,
            error="Failed to authorize. Code may have expired.",
        )
