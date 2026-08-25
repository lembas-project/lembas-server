from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_github_user_data
from app.database import get_db
from app.database.models import User
from app.services.user_service import get_user_by_github_id
from app.settings import Settings


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    """Resolve the ORM User row for the current authenticated user."""
    if access_token is None:
        return None

    if config.dummy_auth:
        return None

    github_user = await get_github_user_data(access_token)
    return await get_user_by_github_id(db, github_user.id)
