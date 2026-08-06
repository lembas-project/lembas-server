import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import exchange_code_for_token, get_github_user_data
from app.database import get_db
from app.dependencies import config, current_user
from app.schemas import User
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
        "user": user.model_dump() if user else None,
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
