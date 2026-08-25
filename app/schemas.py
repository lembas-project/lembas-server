from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class User(BaseModel):
    """User schema for API responses."""

    username: str
    avatar_url: str = ""


class CaseStatus(StrEnum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class CaseRunCreate(BaseModel):
    """Payload for creating a case run."""

    case_id: str = Field(description="Content-addressed case ID (SHA-256 hash)")
    handler_fqn: str = Field(description="Fully qualified name of the case handler")
    inputs: dict[str, Any] = Field(description="Case input parameters")


class CaseRun(BaseModel):
    """A single case execution within a study."""

    case_id: str = Field(description="Content-addressed case ID (SHA-256 hash)")
    handler_fqn: str = Field(description="Fully qualified name of the case handler")
    inputs: dict[str, Any] = Field(description="Case input parameters")
    status: CaseStatus = CaseStatus.pending
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None


class HandlerSchema(BaseModel):
    """A handler schema included with a study."""

    name: str = Field(description="Handler class name")
    schema_fingerprint: str = Field(description="Content-addressed fingerprint (SHA-256[:16])")
    schema_: dict[str, Any] = Field(alias="schema", description="Full JSON Schema")


class StudyCreate(BaseModel):
    """Payload for creating/registering a study."""

    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    plugins_declared: list[str] = Field(default_factory=list)
    handlers: list[HandlerSchema] = Field(default_factory=list)
    cases: list[CaseRunCreate] = Field(default_factory=list)


class Study(BaseModel):
    """A named, versioned collection of case runs."""

    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    plugins_declared: list[str] = Field(default_factory=list)
    handlers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    cases: dict[str, CaseRun] = Field(default_factory=dict)
    created_at: datetime
    pushed_by: str | None = None


class CaseStatusUpdate(BaseModel):
    """Payload for updating a case's status."""

    status: CaseStatus
    duration_seconds: float | None = None
    results: dict[str, Any] | None = None
    environment: dict[str, str] | None = None
    error_message: str | None = None


class StudyResponse(BaseModel):
    """API response format for study detail (matches UI expectations)."""

    study_id: str
    meta: dict[str, Any]
    handlers: dict[str, dict[str, Any]]
    pushed_at: datetime
    pushed_by: str | None
    runs: list[dict[str, Any]]

    @classmethod
    def from_study(cls, study: "Study") -> "StudyResponse":
        runs = [
            {
                "case_id": case.case_id,
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
            study_id=study.id,
            meta={
                "name": study.name,
                "description": study.description,
                "tags": study.tags,
                "plugins": study.plugins_declared,
            },
            handlers=study.handlers,
            pushed_at=study.created_at,
            pushed_by=study.pushed_by,
            runs=runs,
        )
