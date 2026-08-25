"""Tests for database utilities and types."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from sqlalchemy import Integer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.models import TZDateTime


class _TestBase(DeclarativeBase):
    pass


class TimestampModel(_TestBase):
    """Test model for TZDateTime tests."""

    __tablename__ = "test_timestamps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(TZDateTime)


@pytest.fixture
async def ts_table(db: AsyncSession) -> None:
    """Create the test table."""
    from app.database import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(TimestampModel.metadata.create_all, checkfirst=True)


async def test_tzdatetime_stores_and_retrieves_utc(db: AsyncSession, ts_table: None) -> None:
    now = datetime.now(UTC)
    model = TimestampModel(ts=now)
    db.add(model)
    await db.commit()
    model_id = model.id

    db.expire_all()
    result = await db.execute(select(TimestampModel).where(TimestampModel.id == model_id))
    row = result.scalar_one()

    assert row.ts.tzinfo == UTC
    assert row.ts == now


async def test_tzdatetime_converts_other_timezones_to_utc(
    db: AsyncSession, ts_table: None
) -> None:
    eastern = timezone(timedelta(hours=-5))
    eastern_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=eastern)
    expected_utc = datetime(2026, 6, 15, 17, 0, 0, tzinfo=UTC)

    model = TimestampModel(ts=eastern_time)
    db.add(model)
    await db.commit()
    model_id = model.id

    db.expire_all()
    result = await db.execute(select(TimestampModel).where(TimestampModel.id == model_id))
    row = result.scalar_one()

    assert row.ts.tzinfo == UTC
    assert row.ts == expected_utc


async def test_tzdatetime_handles_naive_datetime(db: AsyncSession, ts_table: None) -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    model = TimestampModel(ts=naive)
    db.add(model)
    await db.commit()
    model_id = model.id

    db.expire_all()
    result = await db.execute(select(TimestampModel).where(TimestampModel.id == model_id))
    row = result.scalar_one()

    assert row.ts.tzinfo == UTC
    assert row.ts.replace(tzinfo=None) == naive
