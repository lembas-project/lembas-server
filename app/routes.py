import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.auth import exchange_code_for_token
from app.components import Homepage
from app.dependencies import config, current_user, is_partial_request
from app.models import CaseStatusUpdate, Study, StudyCreate, StudyResponse, User
from app.settings import Settings
from app.templates import render_template

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home(request: Request) -> RedirectResponse:
    return RedirectResponse(request.url_for("studies_gallery"))


@router.get("/studies")
async def studies_gallery(request: Request) -> HTMLResponse:
    """Show a gallery of all studies."""
    studies = await db.get_all_studies()
    return render_template("studies_gallery.html", studies=studies)


@router.get("/ui/studies/{study_id}")
async def study_ui(request: Request, study_id: str) -> HTMLResponse:
    """Render the study detail UI."""
    study = await db.get_study(study_id)
    study_name = study.name if study else "Study"
    return render_template("study.html", study_id=study_id, study_name=study_name)


@router.get("/ui/demo")
async def demo_ui(request: Request) -> HTMLResponse:
    """Render demo UI with mock data."""
    return render_template("study.html", study_id="demo", study_name="Demo Study")


@router.get("/projects")
async def get_projects_list(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
    config: Annotated[Settings, Depends(config)],
    is_partial_request: Annotated[bool, Depends(is_partial_request)],
) -> HTMLResponse:
    projects = await db.get_projects()
    if not is_partial_request:
        return Homepage(
            projects=projects,
            login_url=str(request.url_for("auth_login")),
            logout_url=str(request.url_for("auth_logout")),
            user=user,
        ).render()
    else:
        return render_template("partials/project_list.html", projects=projects)


@router.delete("/projects/{id}")
async def delete_project_by_id(request: Request, id: int) -> RedirectResponse:
    """Delete a project by its ID and re-render the projects list."""
    await db.delete_project(id)
    return RedirectResponse(
        request.url_for("get_projects_list"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/api/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/auth/login")
async def auth_login(
    request: Request,
    config: Annotated[Settings, Depends(config)],
) -> RedirectResponse:
    if config.dummy_auth:
        return RedirectResponse(
            request.url_for("auth_callback").include_query_params(code="dummy-code")
        )

    return RedirectResponse(config.login_url)


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Annotated[str, Query],
    config: Annotated[Settings, Depends(config)],
) -> RedirectResponse:
    response = RedirectResponse(request.url_for("home"))

    if access_token := await exchange_code_for_token(code, config):
        response.set_cookie(key="access_token", value=access_token)

    return response


@router.get("/auth/logout")
async def auth_logout(request: Request) -> RedirectResponse:
    # TODO: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-token
    response = RedirectResponse(request.url_for("home"))
    response.delete_cookie(key="access_token")
    return response


# --- Study API Endpoints ---


@router.post("/api/studies", status_code=status.HTTP_201_CREATED)
async def create_study(
    payload: StudyCreate,
    user: Annotated[User | None, Depends(current_user)],
) -> Study:
    """Register a new study with its cases."""
    pushed_by = user.username if user else None
    study = await db.create_study(payload, pushed_by=pushed_by)
    log.info(f"Created study {study.id} with {len(study.cases)} cases")
    return study


@router.get("/api/studies/{study_id}")
async def get_study(study_id: str) -> Study:
    """Fetch a study by ID (raw format)."""
    study = await db.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return study


@router.get("/api/studies/{study_id}/detail")
async def get_study_detail(study_id: str) -> StudyResponse:
    """Fetch a study in UI-friendly format."""
    study = await db.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyResponse.from_study(study)


@router.get("/api/projects/{project_id}/studies")
async def get_project_studies(project_id: int) -> list[Study]:
    """List all studies in a project."""
    return await db.get_studies_by_project(project_id)


@router.patch("/api/studies/{study_id}/cases/{case_id}")
async def update_case_status(
    study_id: str,
    case_id: str,
    update: CaseStatusUpdate,
) -> dict:
    """Update the status of a case within a study."""
    case = await db.update_case_status(study_id, case_id, update)
    if not case:
        raise HTTPException(status_code=404, detail="Study or case not found")
    log.info(f"Updated case {case_id} in study {study_id} to {update.status}")
    return {"status": "ok", "case": case}
