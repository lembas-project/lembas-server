import httpx
from pydantic import BaseModel

from app.schemas import User
from app.settings import Settings


class GitHubUserData(BaseModel):
    """GitHub user data from the API."""

    id: int
    login: str
    avatar_url: str = ""


async def exchange_code_for_token(code: str, config: Settings) -> str | None:
    """Retrieve an access token based on the code from the authorization flow."""
    if config.dummy_auth:
        return "dummy-token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url,
            json=dict(
                client_id=config.client_id,
                client_secret=config.client_secret,
                code=code,
                redirect_url=config.redirect_url,
            ),
            headers={
                "Accept": "application/json",
            },
        )

    data = resp.json()

    return data.get("access_token")


async def get_github_user_data(token: str) -> GitHubUserData:
    """Fetch user data from GitHub API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    return GitHubUserData.model_validate(resp.json())


async def get_user_from_token(token: str) -> User:
    """Get a User model from a GitHub access token."""
    data = await get_github_user_data(token)
    return User(username=data.login, avatar_url=data.avatar_url)
