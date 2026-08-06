from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import (
    get_or_create_user,
    get_user_by_github_id,
    get_user_by_id,
)


async def test_create_new_user(db: AsyncSession) -> None:
    user = await get_or_create_user(
        db,
        github_id=1000001,
        username="newuser",
        avatar_url="https://example.com/avatar.png",
    )

    assert user.id is not None
    assert user.github_id == 1000001
    assert user.username == "newuser"
    assert user.avatar_url == "https://example.com/avatar.png"


async def test_get_existing_user_returns_unchanged(db: AsyncSession) -> None:
    user1 = await get_or_create_user(
        db,
        github_id=99999,
        username="originaluser",
        avatar_url="https://example.com/old.png",
    )
    original_id = user1.id

    user2 = await get_or_create_user(
        db,
        github_id=99999,
        username="differentuser",
        avatar_url="https://example.com/new.png",
    )

    assert user2.id == original_id
    assert user2.username == "originaluser"
    assert user2.avatar_url == "https://example.com/old.png"


async def test_get_user_by_id(db: AsyncSession) -> None:
    user = await get_or_create_user(
        db,
        github_id=11111,
        username="findme",
        avatar_url=None,
    )

    found = await get_user_by_id(db, user.id)
    assert found is not None
    assert found.username == "findme"

    not_found = await get_user_by_id(db, 999999)
    assert not_found is None


async def test_get_user_by_github_id(db: AsyncSession) -> None:
    await get_or_create_user(
        db,
        github_id=22222,
        username="githubuser",
        avatar_url="https://example.com/gh.png",
    )

    found = await get_user_by_github_id(db, 22222)
    assert found is not None
    assert found.username == "githubuser"

    not_found = await get_user_by_github_id(db, 88888)
    assert not_found is None
