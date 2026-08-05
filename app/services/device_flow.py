"""Device flow service for CLI authentication."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import generate_device_code, generate_user_code
from app.database.models import DeviceCode
from app.services.token_service import create_token

DEVICE_CODE_EXPIRY_MINUTES = 15
DEFAULT_POLL_INTERVAL = 5


class DeviceFlowError(Exception):
    """Base class for device flow errors."""

    error: str
    description: str

    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(description)


class AuthorizationPending(DeviceFlowError):
    def __init__(self) -> None:
        super().__init__("authorization_pending", "User has not yet authorized")


class SlowDown(DeviceFlowError):
    def __init__(self) -> None:
        super().__init__("slow_down", "Polling too fast")


class ExpiredToken(DeviceFlowError):
    def __init__(self) -> None:
        super().__init__("expired_token", "Device code has expired")


class AccessDenied(DeviceFlowError):
    def __init__(self) -> None:
        super().__init__("access_denied", "User denied authorization")


async def create_device_code_record(
    db: AsyncSession,
    verification_uri: str,
    token_name: str = "CLI Token",
) -> DeviceCode:
    """Create a new device code for CLI authentication."""
    device_code = generate_device_code()
    user_code = generate_user_code()
    expires_at = datetime.utcnow() + timedelta(minutes=DEVICE_CODE_EXPIRY_MINUTES)

    record = DeviceCode(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        expires_at=expires_at,
        interval=DEFAULT_POLL_INTERVAL,
        token_name=token_name,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_device_code_by_user_code(db: AsyncSession, user_code: str) -> DeviceCode | None:
    """Get a device code record by its user-facing code."""
    user_code = user_code.upper().strip()
    result = await db.execute(
        select(DeviceCode)
        .where(DeviceCode.user_code == user_code)
        .where(DeviceCode.expires_at > datetime.utcnow())
        .where(DeviceCode.authorized_at.is_(None))
    )
    return result.scalar_one_or_none()


async def authorize_device_code(db: AsyncSession, user_code: str, user_id: int) -> bool:
    """Mark a device code as authorized by a user."""
    record = await get_device_code_by_user_code(db, user_code)
    if not record:
        return False

    record.user_id = user_id
    record.authorized_at = datetime.utcnow()
    await db.commit()
    return True


async def poll_device_code(
    db: AsyncSession,
    device_code: str,
    token_expiry_days: int | None = 90,
) -> tuple[str, int]:
    """Poll for device code status.

    Returns:
        Tuple of (token, expires_in_seconds) if authorized.

    Raises:
        AuthorizationPending: User hasn't authorized yet
        ExpiredToken: Device code has expired
    """
    result = await db.execute(select(DeviceCode).where(DeviceCode.device_code == device_code))
    record = result.scalar_one_or_none()

    if not record:
        raise ExpiredToken()

    if record.expires_at < datetime.utcnow():
        await db.delete(record)
        await db.commit()
        raise ExpiredToken()

    if not record.authorized_at or not record.user_id:
        raise AuthorizationPending()

    token, api_token = await create_token(
        db,
        user_id=record.user_id,
        name=record.token_name,
        expires_days=token_expiry_days,
    )

    await db.delete(record)
    await db.commit()

    expires_in = 0
    if api_token.expires_at:
        expires_in = int((api_token.expires_at - datetime.utcnow()).total_seconds())

    return token, expires_in


async def cleanup_expired_codes(db: AsyncSession) -> int:
    """Remove expired device codes. Returns count of deleted records."""
    result = await db.execute(select(DeviceCode).where(DeviceCode.expires_at < datetime.utcnow()))
    expired = list(result.scalars().all())
    for record in expired:
        await db.delete(record)
    await db.commit()
    return len(expired)
