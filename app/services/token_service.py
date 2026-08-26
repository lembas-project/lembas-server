"""Service functions for API token management."""

import logging
import secrets
from datetime import UTC
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import APIToken
from app.database.models import User

log = logging.getLogger(__name__)

TOKEN_PREFIX = "lb_v1"


def _generate_token() -> str:
    """Generate a prefixed, cryptographically secure token.

    Format: lb_v1_<32 random bytes as hex>
    Example: lb_v1_a3f1c9...
    """
    return f"{TOKEN_PREFIX}_{secrets.token_hex(32)}"


async def create_token(db: AsyncSession, user: User, name: str | None = None) -> APIToken:
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
    """Look up the user associated with a raw token string, updating last_used_at.

    Returns None (rather than raising) on any DB error so that auth failures
    always produce a 4xx response rather than a 500.
    """
    try:
        result = await db.execute(
            select(APIToken)
            .where(APIToken.token == raw_token)
            .options(selectinload(APIToken.user))
        )
    except Exception:
        log.warning("Failed to look up token — DB error", exc_info=True)
        return None

    api_token = result.scalar_one_or_none()
    if api_token is None:
        return None

    api_token.last_used_at = datetime.now(UTC)
    await db.commit()

    return api_token.user


async def list_tokens(db: AsyncSession, user: User) -> list[APIToken]:
    """List all tokens for a user."""
    result = await db.execute(
        select(APIToken).where(APIToken.user_id == user.id).order_by(APIToken.created_at.desc())
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
