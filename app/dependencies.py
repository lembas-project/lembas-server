from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request

from app.auth import get_user_from_token
from app.schemas import User
from app.settings import Settings


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(
    config: Annotated[Settings, Depends(config)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    if access_token is None:
        return None

    if config.dummy_auth:
        return User(username="dummy")

    return await get_user_from_token(access_token)
