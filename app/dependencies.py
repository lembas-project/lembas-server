from typing import Annotated

import httpx
from fastapi import Cookie

from app.models import User


async def get_user_from_token(token: str) -> User:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    data = resp.json()
    return User(**data)


async def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> User | None:
    if access_token is not None:
        user = await get_user_from_token(access_token)
        return user
    return None
