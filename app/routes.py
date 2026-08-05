import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.auth import exchange_code_for_token
from app.dependencies import config
from app.settings import Settings

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home() -> dict[str, str]:
    return {"status": "ok"}


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
) -> RedirectResponse:
    response = RedirectResponse(request.url_for("home"))

    if access_token := await exchange_code_for_token(code, config):
        response.set_cookie(key="access_token", value=access_token)

    return response


@router.get("/auth/logout")
async def auth_logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(request.url_for("home"))
    response.delete_cookie(key="access_token")
    return response
