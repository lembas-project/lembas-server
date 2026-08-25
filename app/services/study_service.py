"""Study service for managing study and case records."""

import json
from datetime import UTC
from datetime import datetime

from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Case
from app.database.models import Study
from app.database.queries import build_case_status_update_stmt
from app.enums import CaseStatus
from app.schemas import CaseSchema
from app.schemas import CaseStatusUpdatePayload
from app.schemas import Study as StudySchema
from app.schemas import StudyCreatePayload


def _orm_case_to_schema(case: Case) -> CaseSchema:
    return CaseSchema(
        id=case.id,
        handler_fqn=case.handler_fqn,
        inputs=json.loads(case.inputs) if case.inputs else {},
        status=case.status,
        started_at=case.started_at,
        completed_at=case.completed_at,
        duration_seconds=case.duration_seconds,
        results=json.loads(case.results) if case.results else {},
        error_message=case.error_message,
        environment=json.loads(case.environment) if case.environment else {},
    )


def _orm_study_to_schema(study: Study) -> StudySchema:
    cases = {c.id: _orm_case_to_schema(c) for c in study.cases}
    return StudySchema(
        id=study.id,
        name=study.name,
        description=study.description,
        tags=json.loads(study.tags) if study.tags else [],
        plugins_declared=json.loads(study.plugins_declared) if study.plugins_declared else [],
        created_at=study.created_at,
        pushed_by=study.pushed_by.username,
        cases=cases,
    )


def _study_query(study_id: str | None = None) -> Select[tuple[Study]]:
    q = select(Study).options(
        selectinload(Study.cases),
        selectinload(Study.pushed_by),
    )
    if study_id is not None:
        q = q.where(Study.id == study_id)
    return q


async def create_study(
    db: AsyncSession, payload: StudyCreatePayload, pushed_by_id: str
) -> StudySchema:
    study = Study(
        name=payload.name,
        description=payload.description,
        tags=json.dumps(payload.tags),
        plugins_declared=json.dumps(payload.plugins_declared),
        pushed_by_id=pushed_by_id,
    )
    db.add(study)
    await db.flush()  # populate study.id from ORM default

    for c in payload.cases:
        db.add(
            Case(
                study_id=study.id,
                id=c.id,
                handler_fqn=c.handler_fqn,
                inputs=json.dumps(c.inputs),
                status=CaseStatus.pending,
            )
        )

    await db.commit()

    result = await db.execute(_study_query(study.id))
    study = result.scalar_one()
    return _orm_study_to_schema(study)


async def get_study(db: AsyncSession, study_id: str) -> StudySchema | None:
    result = await db.execute(_study_query(study_id))
    study = result.scalar_one_or_none()
    if study is None:
        return None
    return _orm_study_to_schema(study)


async def get_all_studies(db: AsyncSession) -> list[StudySchema]:
    result = await db.execute(
        select(Study)
        .order_by(Study.created_at.desc())
        .options(selectinload(Study.cases), selectinload(Study.pushed_by))
    )
    return [_orm_study_to_schema(s) for s in result.scalars().all()]


async def update_study(
    db: AsyncSession, study_id: str, payload: StudyCreatePayload
) -> StudySchema | None:
    result = await db.execute(_study_query(study_id))
    study = result.scalar_one_or_none()
    if study is None:
        return None

    study.name = payload.name
    study.description = payload.description
    study.tags = json.dumps(payload.tags)
    study.plugins_declared = json.dumps(payload.plugins_declared)

    # Upsert cases: update existing, insert new ones
    existing = {c.id: c for c in study.cases}
    for c in payload.cases:
        if c.id in existing:
            orm_case = existing[c.id]
            orm_case.handler_fqn = c.handler_fqn
            orm_case.inputs = json.dumps(c.inputs)
        else:
            db.add(
                Case(
                    study_id=study_id,
                    id=c.id,
                    handler_fqn=c.handler_fqn,
                    inputs=json.dumps(c.inputs),
                    status=CaseStatus.pending,
                )
            )

    await db.commit()
    db.expire_all()

    result = await db.execute(_study_query(study_id))
    study = result.scalar_one()
    return _orm_study_to_schema(study)


async def get_study_owner_id(db: AsyncSession, study_id: str) -> str | None:
    """Return just the pushed_by_id for a study, for ownership checks."""
    result = await db.execute(select(Study.pushed_by_id).where(Study.id == study_id))
    row = result.one_or_none()
    return row[0] if row else None


async def delete_study(db: AsyncSession, study_id: str) -> bool:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if study is None:
        return False
    await db.delete(study)
    await db.commit()
    return True


async def update_case_status(
    db: AsyncSession, study_id: str, case_id: str, payload: CaseStatusUpdatePayload
) -> CaseSchema | None:
    stmt = build_case_status_update_stmt(study_id, case_id, payload, datetime.now(UTC))
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    await db.commit()
    return _orm_case_to_schema(row)
