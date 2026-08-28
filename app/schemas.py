from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

from app.enums import CaseStatus as CaseStatus  # re-exported for API consumers


class Page[T](BaseModel):
    """Generic paginated response envelope.

    Wraps a list of items with pagination metadata. Callers should treat
    ``total`` and ``next`` as optional — they will be populated once
    cursor/offset pagination is implemented.
    """

    items: list[T]
    total: int | None = Field(default=None, description="Total number of matching records")
    limit: int | None = Field(default=None, description="Max items returned in this page")
    offset: int | None = Field(default=None, description="Offset of this page")


class StudyUsage(BaseModel):
    """A study that uses a particular handler schema."""

    study_id: str
    study_name: str


class HandlerSchemaResponse(BaseModel):
    """A handler schema with usage information."""

    fingerprint: str
    name: str
    schema_: dict[str, Any] = Field(alias="schema")
    created_at: datetime
    used_by: list[StudyUsage] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DeviceFlowResponse(BaseModel):
    """Returned to the CLI when initiating a device login flow."""

    device_code: str
    user_code: str
    verification_uri: str
    interval: int
    expires_in: int


class DeviceTokenRequest(BaseModel):
    """Payload for polling the device token endpoint."""

    device_code: str
    token_name: str | None = Field(default=None, description="Optional label for the token")


class DeviceTokenResponse(BaseModel):
    """Returned when the device flow completes successfully."""

    token: str
    token_name: str | None = None


class DevicePendingResponse(BaseModel):
    """Returned while the user has not yet approved the device flow."""

    error: Literal["authorization_pending", "slow_down"]
    interval: int | None = None  # updated interval if slow_down


class UserResponse(BaseModel):
    """Public-facing user representation."""

    id: str
    username: str
    avatar_url: str | None = None


class TokenCreatePayload(BaseModel):
    """Payload for creating an API token."""

    name: str | None = Field(default=None, description="Optional human-readable label")


class TokenResponse(BaseModel):
    """Response after creating a token. The raw token is only returned once."""

    id: str
    name: str | None
    token: str
    created_at: datetime


class TokenMetadata(BaseModel):
    """Token metadata for listing — does not include the raw token value."""

    id: str
    name: str | None
    created_at: datetime
    last_used_at: datetime | None


class CaseRunCreate(BaseModel):
    """Payload for creating a case run."""

    id: str = Field(description="Content-addressed case ID (SHA-256 hash)")
    handler_fqn: str = Field(description="Fully qualified name of the case handler")
    inputs: dict[str, Any] = Field(description="Case input parameters")


class CaseSchema(BaseModel):
    """A single case execution within a study."""

    id: str = Field(description="Content-addressed case ID (SHA-256 hash)")
    handler_fqn: str = Field(description="Fully qualified name of the case handler")
    inputs: dict[str, Any] = Field(description="Case input parameters")
    status: CaseStatus = CaseStatus.pending
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None


class HandlerSchemaPayload(BaseModel):
    """A handler schema submitted alongside a study."""

    fingerprint: str = Field(description="Content-addressed fingerprint (SHA-256[:16] or full)")
    name: str = Field(description="Handler class name")
    schema_: dict[str, Any] = Field(alias="schema", description="Full JSON Schema blob")

    model_config = {"populate_by_name": True}


class StudyCreatePayload(BaseModel):
    """Payload for creating/registering a study."""

    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    plugins_declared: list[str] = Field(default_factory=list)
    handlers: list[HandlerSchemaPayload] = Field(default_factory=list)
    cases: list[CaseRunCreate] = Field(default_factory=list)


class Study(BaseModel):
    """A named, versioned collection of case runs."""

    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    plugins_declared: list[str] = Field(default_factory=list)
    cases: dict[str, CaseSchema] = Field(default_factory=dict)
    created_at: datetime
    pushed_by: str


class CaseStatusUpdatePayload(BaseModel):
    """Payload for updating a case's status."""

    status: CaseStatus
    duration_seconds: float | None = None
    results: dict[str, Any] | None = None
    environment: dict[str, str] | None = None
    error_message: str | None = None


class StudyResponse(BaseModel):
    """API response format for study detail (matches UI expectations)."""

    id: str
    meta: dict[str, Any]
    pushed_at: datetime
    pushed_by: str
    runs: list[dict[str, Any]]

    @classmethod
    def from_study(cls, study: "Study") -> "StudyResponse":
        runs = [
            {
                "case_id": case.id,
                "handler": case.handler_fqn.split(".")[-1],
                "inputs": case.inputs,
                "status": case.status.value,
                "started_at": case.started_at.isoformat() if case.started_at else None,
                "completed_at": case.completed_at.isoformat() if case.completed_at else None,
                "duration_seconds": case.duration_seconds,
                "results": case.results,
                "environment": case.environment,
            }
            for case in study.cases.values()
        ]
        return cls(
            id=study.id,
            meta={
                "name": study.name,
                "description": study.description,
                "tags": study.tags,
                "plugins": study.plugins_declared,
            },
            pushed_at=study.created_at,
            pushed_by=study.pushed_by,
            runs=runs,
        )
