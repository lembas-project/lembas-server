"""Database query helpers — reusable SQL statement builders."""

import json
from datetime import datetime

from sqlalchemy import Update
from sqlalchemy import case as sa_case
from sqlalchemy import literal
from sqlalchemy import update as sa_update

from app.database.models import Case
from app.enums import CaseStatus
from app.schemas import CaseStatusUpdatePayload


def build_case_status_update_stmt(
    study_id: str, case_id: str, payload: CaseStatusUpdatePayload, now: datetime
) -> Update:
    """Build an atomic UPDATE statement for a case's status.

    Uses a SQL CASE expression for started_at so that the first
    transition to 'running' sets the timestamp without overwriting
    a value that was already set — eliminating any read-modify-write race.
    """
    values: dict = {"status": payload.status}

    if payload.status == CaseStatus.running:
        values["started_at"] = sa_case(
            (Case.started_at.is_(None), literal(now)),
            else_=Case.started_at,
        )
    elif payload.status in (CaseStatus.complete, CaseStatus.failed):
        values["completed_at"] = now

    if payload.error_message is not None:
        values["error_message"] = payload.error_message
    if payload.duration_seconds is not None:
        values["duration_seconds"] = payload.duration_seconds
    if payload.results is not None:
        values["results"] = json.dumps(payload.results)
    if payload.environment is not None:
        values["environment"] = json.dumps(payload.environment)

    return (
        sa_update(Case)
        .where(Case.study_id == study_id, Case.id == case_id)
        .values(**values)
        .returning(Case)
    )
