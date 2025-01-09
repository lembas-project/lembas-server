import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

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
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url,
            json=dict(
                client_id=config.client_id,
                client_secret=config.client_secret,
                code=code,
                redirect_url=config.redirect_url,
            ),
            headers={
                "Accept": "application/json",
            },
        )
    # TODO: Add Error handling for non-200 responses
    data = resp.json()
    access_token = data["access_token"]

    response = RedirectResponse("/")
    response.set_cookie(key="access_token", value=access_token)
    return response


@router.get("/auth/logout")
async def auth_logout() -> RedirectResponse:
    # TODO: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-token
    response = RedirectResponse("/")
    response.delete_cookie(key="access_token")
    return response
