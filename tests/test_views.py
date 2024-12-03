from httpx import AsyncClient


async def test_get_home(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "Demo Stream" in response.text
