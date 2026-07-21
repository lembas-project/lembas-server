from datetime import UTC, datetime
from uuid import uuid4

from app.models import (
    CaseRun,
    CaseStatus,
    CaseStatusUpdate,
    Project,
    Study,
    StudyCreate,
)

PROJECTS: dict[int, Project] = {i: Project(id=i, name=f"Project {i}") for i in range(1, 11)}
STUDIES: dict[str, Study] = {}


async def get_projects() -> list[Project]:
    return [project for id, project in PROJECTS.items()]


async def add_project(name: str) -> Project:
    new_id = max(id for id in PROJECTS.keys()) + 1
    project = Project(id=new_id, name=name)
    PROJECTS[new_id] = project
    return project


async def delete_project(id: int) -> Project | None:
    return PROJECTS.pop(id, None)


async def create_study(payload: StudyCreate, pushed_by: str | None = None) -> Study:
    study_id = str(uuid4())
    cases = {
        c.case_id: CaseRun(
            case_id=c.case_id,
            handler_fqn=c.handler_fqn,
            inputs=c.inputs,
        )
        for c in payload.cases
    }
    study = Study(
        id=study_id,
        name=payload.name,
        project_id=payload.project_id,
        description=payload.description,
        tags=payload.tags,
        plugins_declared=payload.plugins_declared,
        cases=cases,
        created_at=datetime.now(UTC),
        pushed_by=pushed_by,
    )
    STUDIES[study_id] = study
    return study


async def get_study(study_id: str) -> Study | None:
    return STUDIES.get(study_id)


async def get_studies_by_project(project_id: int) -> list[Study]:
    return [s for s in STUDIES.values() if s.project_id == project_id]


async def get_all_studies() -> list[Study]:
    return list(STUDIES.values())


async def update_case_status(
    study_id: str, case_id: str, update: CaseStatusUpdate
) -> CaseRun | None:
    study = STUDIES.get(study_id)
    if not study or case_id not in study.cases:
        return None

    case = study.cases[case_id]
    now = datetime.now(UTC)

    if update.status == CaseStatus.running and case.started_at is None:
        case.started_at = now
    elif update.status in (CaseStatus.complete, CaseStatus.failed):
        case.completed_at = now

    case.status = update.status
    if update.error_message is not None:
        case.error_message = update.error_message
    if update.duration_seconds is not None:
        case.duration_seconds = update.duration_seconds
    if update.results is not None:
        case.results = update.results
    if update.environment is not None:
        case.environment = update.environment

    return case
