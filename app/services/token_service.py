"""Service functions for API token management."""

import secrets
from datetime import UTC
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import APIToken
from app.database.models import User


def _generate_token() -> str:
    """Generate a cryptographically secure 32-byte (64 hex char) token."""
    return secrets.token_hex(32)


async def create_token(
    db: AsyncSession, user: User, name: str | None = None
) -> APIToken:
    """Create and persist a new API token for the given user."""
    token = APIToken(
        user_id=user.id,
        token=_generate_token(),
        name=name,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_user_by_token(db: AsyncSession, raw_token: str) -> User | None:
    """Look up the user associated with a raw token string, updating last_used_at."""
    result = await db.execute(
        select(APIToken)
        .where(APIToken.token == raw_token)
        .options(selectinload(APIToken.user))
    )
    api_token = result.scalar_one_or_none()
    if api_token is None:
        return None

    api_token.last_used_at = datetime.now(UTC)
    await db.commit()

    return api_token.user


async def list_tokens(db: AsyncSession, user: User) -> list[APIToken]:
    """List all tokens for a user."""
    result = await db.execute(
        select(APIToken)
        .where(APIToken.user_id == user.id)
        .order_by(APIToken.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_token(db: AsyncSession, token_id: str, user: User) -> bool:
    """Delete a token by ID. Returns False if not found or not owned by user."""
    result = await db.execute(
        select(APIToken).where(APIToken.id == token_id, APIToken.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    if token is None:
        return False
    await db.delete(token)
    await db.commit()
    return True
