import httpx

from app.models import User
from app.settings import Settings


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
