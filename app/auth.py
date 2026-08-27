import httpx
from pydantic import BaseModel

from app.settings import Settings

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubUserData(BaseModel):
    """GitHub user data from the API."""

    id: int
    login: str
    avatar_url: str = ""


class DeviceCodeResponse(BaseModel):
    """Response from initiating a device flow."""

    device_code: str
    user_code: str
    verification_uri: str
    interval: int
    expires_in: int


class DeviceTokenResult(BaseModel):
    """Result of polling for a device token."""

    access_token: str | None = None
    error: str | None = None  # e.g. "authorization_pending", "slow_down", "expired_token"
    interval: int | None = None  # updated polling interval when error == "slow_down"


async def request_device_code(config: Settings) -> DeviceCodeResponse:
    """Initiate a GitHub device flow and return the codes to show the user."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_DEVICE_CODE_URL,
            json={"client_id": config.client_id, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
    resp.raise_for_status()
    return DeviceCodeResponse.model_validate(resp.json())


async def poll_device_token(device_code: str, config: Settings) -> DeviceTokenResult:
    """Poll GitHub once for a device flow access token.

    The caller is responsible for respecting the polling interval.
    Returns DeviceTokenResult with either an access_token or an error string.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
    resp.raise_for_status()
    data = resp.json()
    return DeviceTokenResult(
        access_token=data.get("access_token"),
        error=data.get("error"),
        interval=data.get("interval"),
    )


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
