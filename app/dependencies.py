from typing import Annotated

import httpx
from fastapi import Cookie, Header, Request

from app.models import User
from app.settings import Settings


async def _get_user_from_token(token: str) -> User:
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


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(access_token: Annotated[str | None, Cookie()] = None) -> User | None:
    if access_token is not None:
        user = await _get_user_from_token(access_token)
        return user
    return None


async def is_partial_request(
    from_htmx: Annotated[str, Header(alias="hx-request")] = "",
) -> bool:
    return bool(from_htmx)
