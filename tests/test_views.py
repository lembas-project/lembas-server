from httpx import AsyncClient


async def test_root_redirects_to_studies(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/studies"


async def test_studies_gallery_renders(client: AsyncClient) -> None:
    response = await client.get("/studies", follow_redirects=True)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
