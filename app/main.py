import logging
from typing import Annotated

import httpx
from fastapi import Cookie, Depends, FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import config, templates
from app.templates import render_template

log = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates.init_app(app)


class User(BaseModel):
    username: str = Field(validation_alias="login")
    name: str | None = None
    avatar_url: str = ""


async def get_user_from_token(token: str) -> User:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    data = resp.json()
    return User(**data)


async def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> User | None:
    if access_token is not None:
        user = await get_user_from_token(access_token)
        return user
    return None


@app.get("/")
async def home(user: Annotated[User | None, Depends(get_current_user)]) -> HTMLResponse:
    return render_template(
        "home.html",
        projects=[{"name": "project 1"}],
        login_url=config.LOGIN_URL,
        # TODO: Use request.url_for
        logout_url="/auth/logout",
        user=user,
    )


@app.get("/auth/callback")
async def auth_callback(code: str) -> RedirectResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.TOKEN_URL,
            json=dict(
                client_id=config.CLIENT_ID,
                client_secret=config.CLIENT_SECRET,
                code=code,
                redirect_url=config.REDIRECT_URL,
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


@app.get("/auth/logout")
async def auth_logout() -> RedirectResponse:
    # TODO: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-token
    response = RedirectResponse("/")
    response.delete_cookie(key="access_token")
    return response


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}
