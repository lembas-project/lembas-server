"""Tests for the device authorization flow endpoints."""

from unittest.mock import AsyncMock
from unittest.mock import patch

from httpx import AsyncClient

from app.auth import DeviceCodeResponse
from app.auth import DeviceTokenResult


async def test_device_flow_start(client: AsyncClient) -> None:
    mock_response = DeviceCodeResponse(
        device_code="dev-code-abc",
        user_code="ABCD-1234",
        verification_uri="https://github.com/login/device",
        interval=5,
        expires_in=300,
    )
    with patch(
        "app.routes.request_device_code", new_callable=AsyncMock, return_value=mock_response
    ):
        response = await client.get("/api/auth/device")

    assert response.status_code == 200
    data = response.json()
    assert data["user_code"] == "ABCD-1234"
    assert data["verification_uri"] == "https://github.com/login/device"
    assert data["interval"] == 5
    assert data["expires_in"] == 300
    # device_code is included so the client can poll
    assert data["device_code"] == "dev-code-abc"


async def test_device_flow_token_pending(client: AsyncClient) -> None:
    mock_result = DeviceTokenResult(error="authorization_pending")
    with patch("app.routes.poll_device_token", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post(
            "/api/auth/device/token",
            json={"device_code": "dev-code-abc"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] == "authorization_pending"


async def test_device_flow_token_slow_down(client: AsyncClient) -> None:
    mock_result = DeviceTokenResult(error="slow_down", interval=10)
    with patch("app.routes.poll_device_token", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post(
            "/api/auth/device/token",
            json={"device_code": "dev-code-abc"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] == "slow_down"
    assert data["interval"] == 10


async def test_device_flow_token_success(client: AsyncClient) -> None:
    from app.auth import GitHubUserData

    mock_result = DeviceTokenResult(access_token="ghu_github_token")
    mock_github_user = GitHubUserData(id=42, login="testuser", avatar_url="")

    with (
        patch("app.routes.poll_device_token", new_callable=AsyncMock, return_value=mock_result),
        patch(
            "app.routes.get_github_user_data",
            new_callable=AsyncMock,
            return_value=mock_github_user,
        ),
    ):
        response = await client.post(
            "/api/auth/device/token",
            json={"device_code": "dev-code-abc", "token_name": "my-laptop"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["token"].startswith("lb_v1_")
    assert data["token_name"] == "my-laptop"


async def test_device_flow_token_expired(client: AsyncClient) -> None:
    mock_result = DeviceTokenResult(error="expired_token")
    with patch("app.routes.poll_device_token", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post(
            "/api/auth/device/token",
            json={"device_code": "dev-code-abc"},
        )

    assert response.status_code == 400
    assert "expired_token" in response.json()["detail"]
