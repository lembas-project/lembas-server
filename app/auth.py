import httpx

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
