import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import exchange_code_for_token
from app.components import Homepage
from app.dependencies import config, current_user
from app.models import User
from app.settings import Settings

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home(
    user: Annotated[User | None, Depends(current_user)],
    config: Annotated[Settings, Depends(config)],
) -> HTMLResponse:
    return Homepage(
        projects=[{"name": "project 1"}],
        login_url=config.login_url,
        # TODO: Use request.url_for
        logout_url="/auth/logout",
        user=user,
    ).render()


@router.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/auth/callback")
async def auth_callback(
    code: str,
    config: Annotated[Settings, Depends(config)],
) -> RedirectResponse:
    response = RedirectResponse("/")

    if access_token := await exchange_code_for_token(code, config):
        response.set_cookie(key="access_token", value=access_token)

    return response


@router.get("/auth/logout")
async def auth_logout() -> RedirectResponse:
    # TODO: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-token
    response = RedirectResponse("/")
    response.delete_cookie(key="access_token")
    return response
