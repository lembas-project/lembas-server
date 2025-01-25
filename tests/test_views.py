from httpx import AsyncClient


async def test_get_home(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert "Lembas" in response.text
