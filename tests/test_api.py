from unittest.mock import AsyncMock
from unittest.mock import Mock

from httpx import AsyncClient

from app.auth import GitHubUserData


async def test_get_health(client: AsyncClient) -> None:
    response = await client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


async def test_auth_callback_success(client: AsyncClient, mocker: Mock, base_url: str) -> None:
    mocker.patch("app.routes.exchange_code_for_token", return_value="valid-access-token")
    mock_github_user = GitHubUserData(
        id=12345,
        login="testuser",
        avatar_url="https://example.com/avatar.png",
    )
    mocker.patch(
        "app.routes.get_github_user_data",
        new_callable=AsyncMock,
        return_value=mock_github_user,
    )

    response = await client.get(
        "/auth/callback", params={"code": "valid-code"}, follow_redirects=False
    )

    assert response.status_code == 307
    assert response.headers["Location"] == f"{base_url}/"

    assert response.cookies.get("access_token") == "valid-access-token"


async def test_auth_callback_redirect_on_failure(
    client: AsyncClient, mocker: Mock, base_url: str
) -> None:
    mock = mocker.patch("app.routes.exchange_code_for_token", return_value=None)

    response = await client.get(
        "/auth/callback", params={"code": "bad-code"}, follow_redirects=False
    )

    mock.assert_called_once()

    assert response.status_code == 307
    assert response.headers["Location"] == f"{base_url}/"

    assert response.cookies.get("access_token") is None
