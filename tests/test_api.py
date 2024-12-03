from httpx import AsyncClient


async def test_get_health(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
