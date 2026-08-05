"""Token service for managing API tokens."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import generate_api_token, get_token_prefix, hash_token
from app.database.models import APIToken, User


async def create_token(
    db: AsyncSession,
    user_id: int,
    name: str,
    expires_days: int | None = 90,
) -> tuple[str, APIToken]:
    """Create a new API token for a user.

    Returns:
        Tuple of (full_token, token_record). The full_token is only returned once
        and should be shown to the user immediately.
    """
    token, token_hash = generate_api_token()
    prefix = get_token_prefix(token)

    expires_at = None
    if expires_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    api_token = APIToken(
        user_id=user_id,
        token_hash=token_hash,
        token_prefix=prefix,
        name=name,
        expires_at=expires_at,
    )
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)

    return token, api_token


async def validate_bearer_token(db: AsyncSession, token: str) -> User | None:
    """Validate a bearer token and return the associated user.

    Also updates last_used_at timestamp.
    """
    token_hash = hash_token(token)

    result = await db.execute(
        select(APIToken)
        .where(APIToken.token_hash == token_hash)
        .where(APIToken.revoked_at.is_(None))
    )
    api_token = result.scalar_one_or_none()

    if not api_token:
        return None

    if api_token.expires_at and api_token.expires_at < datetime.utcnow():
        return None

    api_token.last_used_at = datetime.utcnow()
    await db.commit()

    user_result = await db.execute(select(User).where(User.id == api_token.user_id))
    return user_result.scalar_one_or_none()


async def list_user_tokens(db: AsyncSession, user_id: int) -> list[APIToken]:
    """List all non-revoked tokens for a user."""
    result = await db.execute(
        select(APIToken)
        .where(APIToken.user_id == user_id)
        .where(APIToken.revoked_at.is_(None))
        .order_by(APIToken.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_token(db: AsyncSession, user_id: int, token_id: int) -> bool:
    """Revoke a token. Returns True if token was found and revoked."""
    result = await db.execute(
        select(APIToken)
        .where(APIToken.id == token_id)
        .where(APIToken.user_id == user_id)
        .where(APIToken.revoked_at.is_(None))
    )
    api_token = result.scalar_one_or_none()

    if not api_token:
        return False

    api_token.revoked_at = datetime.utcnow()
    await db.commit()
    return True
