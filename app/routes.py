import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.auth import exchange_code_for_token
from app.components import Homepage
from app.dependencies import config, current_user, is_partial_request
from app.models import User
from app.settings import Settings
from app.templates import render_template

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home() -> RedirectResponse:
    return RedirectResponse("/projects")


@router.get("/projects")
async def get_projects_list(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
    config: Annotated[Settings, Depends(config)],
    is_partial_request: Annotated[bool, Depends(is_partial_request)] = False,
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
