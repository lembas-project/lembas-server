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
from app.schemas import CaseRun
from app.schemas import CaseStatus
from app.schemas import CaseStatusUpdate
from app.schemas import Study as StudySchema
from app.schemas import StudyCreate


def _orm_case_to_schema(case: Case) -> CaseRun:
    return CaseRun(
        id=case.id,
        handler_fqn=case.handler_fqn,
        inputs=json.loads(case.inputs) if case.inputs else {},
        status=CaseStatus(case.status),
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
        pushed_by_id=study.pushed_by_id,
        pushed_by=study.pushed_by.username if study.pushed_by else None,
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
    db: AsyncSession, payload: StudyCreate, pushed_by_id: str | None = None
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
                status="pending",
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
    db: AsyncSession, study_id: str, payload: StudyCreate
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
                    status="pending",
                )
            )

    await db.commit()
    db.expire_all()

    result = await db.execute(_study_query(study_id))
    study = result.scalar_one()
    return _orm_study_to_schema(study)


async def delete_study(db: AsyncSession, study_id: str) -> bool:
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if study is None:
        return False
    await db.delete(study)
    await db.commit()
    return True


async def update_case_status(
    db: AsyncSession, study_id: str, case_id: str, update: CaseStatusUpdate
) -> CaseRun | None:
    result = await db.execute(select(Case).where(Case.study_id == study_id, Case.id == case_id))
    case = result.scalar_one_or_none()
    if case is None:
        return None

    now = datetime.now(UTC)
    case.status = update.status.value

    if update.status == CaseStatus.running and case.started_at is None:
        case.started_at = now
    elif update.status in (CaseStatus.complete, CaseStatus.failed):
        case.completed_at = now

    if update.error_message is not None:
        case.error_message = update.error_message
    if update.duration_seconds is not None:
        case.duration_seconds = update.duration_seconds
    if update.results is not None:
        case.results = json.dumps(update.results)
    if update.environment is not None:
        case.environment = json.dumps(update.environment)

    await db.commit()
    await db.refresh(case)
    return _orm_case_to_schema(case)
