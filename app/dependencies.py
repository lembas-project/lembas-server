from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_user_from_token
from app.database import get_db
from app.database.models import User as UserOrm
from app.schemas import User
from app.services.user_service import get_user_by_github_id
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


async def current_user_orm(
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> UserOrm | None:
    """Resolve the ORM User row for the current authenticated user."""
    if access_token is None:
        return None

    if config.dummy_auth:
        return None

    user_schema = await get_user_from_token(access_token)
    if user_schema is None:
        return None

    from app.auth import get_github_user_data

    github_user = await get_github_user_data(access_token)
    return await get_user_by_github_id(db, github_user.id)
