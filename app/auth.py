import httpx

from app.models import User
from app.settings import Settings


class GitHubUserData:
    """Raw GitHub user data."""

    def __init__(self, data: dict) -> None:
        self.id: int = data["id"]
        self.login: str = data["login"]
        self.avatar_url: str = data.get("avatar_url", "")


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
    return GitHubUserData(resp.json())


async def get_user_from_token(token: str) -> User:
    """Get a User model from a GitHub access token."""
    data = await get_github_user_data(token)
    return User(login=data.login, avatar_url=data.avatar_url)
