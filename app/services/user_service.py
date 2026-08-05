"""User service for managing user records."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import encrypt_value
from app.database.models import User


async def get_or_create_user(
    db: AsyncSession,
    github_id: int,
    username: str,
    name: str | None,
    avatar_url: str | None,
    github_access_token: str | None = None,
    encryption_key: str = "",
) -> User:
    """Get an existing user by GitHub ID or create a new one."""
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user:
        user.username = username
        user.name = name
        user.avatar_url = avatar_url
        user.updated_at = datetime.utcnow()
        if github_access_token:
            user.github_access_token_encrypted = encrypt_value(github_access_token, encryption_key)
        await db.commit()
        return user

    user = User(
        github_id=github_id,
        username=username,
        name=name,
        avatar_url=avatar_url,
        github_access_token_encrypted=(
            encrypt_value(github_access_token, encryption_key) if github_access_token else None
        ),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get a user by their database ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_github_id(db: AsyncSession, github_id: int) -> User | None:
    """Get a user by their GitHub ID."""
    result = await db.execute(select(User).where(User.github_id == github_id))
    return result.scalar_one_or_none()
