from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_github_user_data
from app.database import get_db
from app.database.models import User
from app.services.token_service import get_user_by_token
from app.services.user_service import get_user_by_github_id
from app.settings import Settings

_bearer = HTTPBearer(auto_error=False)


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    """Resolve the ORM User for the current request.

    Checks in order:
    1. Authorization: Bearer <token> header — API token (for CLI/programmatic use)
    2. access_token cookie — GitHub OAuth session (for browser use)
    """
    if bearer is not None:
        return await get_user_by_token(db, bearer.credentials)

    if access_token is None:
        return None

    if config.dummy_auth:
        return None

    github_user = await get_github_user_data(access_token)
    return await get_user_by_github_id(db, github_user.id)
