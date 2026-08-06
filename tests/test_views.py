from httpx import AsyncClient


async def test_get_home_anonymous(client: AsyncClient, base_url: str) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"] is None
    assert data["login_url"] == f"{base_url}/auth/login"
    assert data["logout_url"] == f"{base_url}/auth/logout"


async def test_get_home_logged_in(client: AsyncClient, base_url: str) -> None:
    client.cookies.set("access_token", "dummy-token")
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == "dummy"
    assert data["login_url"] == f"{base_url}/auth/login"
    assert data["logout_url"] == f"{base_url}/auth/logout"
