"""Service functions for API token management."""

import hashlib
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


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw token value.

    Only the hash is stored in the database. The raw token is shown to the
    user once at creation time and never persisted.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_token(
    db: AsyncSession, user: User, name: str | None = None
) -> tuple[APIToken, str]:
    """Create a new API token, storing only its hash.

    Returns a (APIToken, raw_token) tuple. The raw token must be shown to
    the user immediately — it is not stored and cannot be recovered later.
    """
    raw_token = _generate_token()
    token = APIToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        name=name,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token, raw_token


async def get_user_by_token(db: AsyncSession, raw_token: str) -> User | None:
    """Look up the user associated with a raw token string, updating last_used_at.

    Returns None (rather than raising) on any DB error so that auth failures
    always produce a 4xx response rather than a 500.
    """
    try:
        result = await db.execute(
            select(APIToken)
            .where(APIToken.token_hash == hash_token(raw_token))
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


async def delete_token_by_value(db: AsyncSession, raw_token: str) -> bool:
    """Delete a token by its raw value. Used for self-revocation on logout."""
    result = await db.execute(
        select(APIToken).where(APIToken.token_hash == hash_token(raw_token))
    )
    token = result.scalar_one_or_none()
    if token is None:
        return False
    await db.delete(token)
    await db.commit()
    return True
