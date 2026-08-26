"""SQLAlchemy ORM models."""

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.types import Uuid

from app.enums import CaseStatus


class TZDateTime(TypeDecorator[datetime]):
    """A DateTime type that stores UTC and returns timezone-aware datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is not None:
            value = value.replace(tzinfo=UTC)
        return value


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_new_uuid)
    github_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now, onupdate=_utc_now)


class Study(Base):
    """A named collection of case runs."""

    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON array
    plugins_declared: Mapped[str | None] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    pushed_by_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    pushed_by: Mapped["User"] = relationship("User")
    cases: Mapped[list["Case"]] = relationship(
        "Case", back_populates="study", cascade="all, delete-orphan"
    )


class Case(Base):
    """A single case execution within a study."""

    __tablename__ = "cases"

    study_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("studies.id"), nullable=False, primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, primary_key=True)
    handler_fqn: Mapped[str] = mapped_column(Text, nullable=False)
    inputs: Mapped[str | None] = mapped_column(Text)  # JSON dict
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), nullable=False, default=CaseStatus.pending
    )
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    results: Mapped[str | None] = mapped_column(Text)  # JSON dict
    error_message: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)  # JSON dict

    study: Mapped["Study"] = relationship("Study", back_populates="cases")


class APIToken(Base):
    """A long-lived API token associated with a user account."""

    __tablename__ = "api_tokens"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))  # optional human label
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(TZDateTime)

    user: Mapped["User"] = relationship("User")
