from httpx import AsyncClient


async def test_get_health(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


async def test_auth_callback_redirect_on_failure(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/callback", params={"code": "bad-code"}, follow_redirects=False
    )
    assert response.status_code == 307
    assert response.headers["Location"] == "/"

    assert response.cookies.get("access_token") is None
