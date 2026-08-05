from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_user_from_token
from app.database import get_db
from app.database.models import User as DBUser
from app.models import User
from app.services.token_service import validate_bearer_token
from app.settings import Settings


def config(request: Request) -> Settings:
    return request.app.extra["config"]


async def current_user(
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Authenticate user via Bearer token (CLI) or cookie (web)."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if token.startswith("lb_v1_"):
            db_user = await validate_bearer_token(db, token)
            if db_user:
                return User(
                    login=db_user.username,
                    name=db_user.name,
                    avatar_url=db_user.avatar_url or "",
                )
        return None

    if access_token is None:
        return None

    if config.dummy_auth:
        return User(login="dummy")

    return await get_user_from_token(access_token)


async def current_db_user(
    config: Annotated[Settings, Depends(config)],
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> DBUser | None:
    """Get the database user record for authenticated user."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if token.startswith("lb_v1_"):
            return await validate_bearer_token(db, token)
        return None

    return None


async def require_user(
    user: Annotated[User | None, Depends(current_user)],
) -> User:
    """Dependency that requires authentication."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_db_user(
    db_user: Annotated[DBUser | None, Depends(current_db_user)],
) -> DBUser:
    """Dependency that requires authentication and returns DB user."""
    if db_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return db_user


async def is_partial_request(
    from_htmx: Annotated[str, Header(alias="hx-request")] = "",
) -> bool:
    return bool(from_htmx)
