from typing import Annotated

from fastapi import Cookie, Depends, Header, Request

from app.auth import get_user_from_token
from app.models import User
from app.settings import Settings


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(
    config: Annotated[Settings, Depends(config)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    if access_token is not None:
        if config.dummy_auth:
            return User(login="dummy")
        user = await get_user_from_token(access_token)
        return user
    return None


async def is_partial_request(
    from_htmx: Annotated[str, Header(alias="hx-request")] = "",
) -> bool:
    return bool(from_htmx)
