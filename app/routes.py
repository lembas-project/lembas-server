import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app import db
from app.auth import exchange_code_for_token
from app.dependencies import config, current_user
from app.models import CaseStatusUpdate, Study, StudyCreate, StudyResponse, User
from app.settings import Settings
from app.storage import compute_hash, get_storage
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


@router.put("/api/studies/{study_id}")
async def update_study(study_id: str, payload: StudyCreate) -> Study:
    """Update an existing study, upserting cases."""
    study = await db.update_study(study_id, payload)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    log.info(f"Updated study {study.id} with {len(study.cases)} cases")
    return study


@router.delete("/api/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(study_id: str) -> None:
    """Delete a study and all its cases."""
    deleted = await db.delete_study(study_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Study not found")
    log.info(f"Deleted study {study_id}")


@router.get("/api/studies/{study_id}/detail")
async def get_study_detail(study_id: str) -> StudyResponse:
    """Fetch a study in UI-friendly format."""
    study = await db.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyResponse.from_study(study)


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


# --- Artifact Storage Endpoints ---


@router.put("/api/studies/{study_id}/cases/{case_id}/files/{path:path}")
async def upload_case_file(
    study_id: str,
    case_id: str,
    path: str,
    file: UploadFile,
) -> dict:
    """Upload a file to a case's storage.

    Files are stored content-addressed by SHA-256 hash, with a mapping
    from path -> hash stored in the case manifest.
    """
    study = await db.get_study(study_id)
    if not study or case_id not in study.cases:
        raise HTTPException(status_code=404, detail="Study or case not found")

    storage = get_storage()
    data = await file.read()
    content_hash = compute_hash(data)

    blob_key = f"blobs/{content_hash[:2]}/{content_hash}"
    if not await storage.exists(blob_key):
        await storage.put(blob_key, data)

    file_key = f"studies/{study_id}/cases/{case_id}/files/{path}"
    await storage.put(file_key, content_hash.encode())

    log.info(f"Uploaded {path} to case {case_id[:8]} ({len(data)} bytes, hash={content_hash[:8]})")
    return {"path": path, "hash": content_hash, "size": len(data)}


@router.get("/api/studies/{study_id}/cases/{case_id}/files/{path:path}")
async def download_case_file(
    study_id: str,
    case_id: str,
    path: str,
) -> Response:
    """Download a file from a case's storage."""
    study = await db.get_study(study_id)
    if not study or case_id not in study.cases:
        raise HTTPException(status_code=404, detail="Study or case not found")

    storage = get_storage()
    file_key = f"studies/{study_id}/cases/{case_id}/files/{path}"

    hash_data = await storage.get(file_key)
    if not hash_data:
        raise HTTPException(status_code=404, detail="File not found")

    content_hash = hash_data.decode()
    blob_key = f"blobs/{content_hash[:2]}/{content_hash}"
    data = await storage.get(blob_key)
    if not data:
        raise HTTPException(status_code=404, detail="Blob not found")

    return Response(content=data, media_type="application/octet-stream")


@router.get("/api/studies/{study_id}/cases/{case_id}/manifest")
async def get_case_manifest(
    study_id: str,
    case_id: str,
) -> dict:
    """Get the file manifest for a case (path -> hash mapping)."""
    study = await db.get_study(study_id)
    if not study or case_id not in study.cases:
        raise HTTPException(status_code=404, detail="Study or case not found")

    storage = get_storage()
    prefix = f"studies/{study_id}/cases/{case_id}/files/"
    manifest = {}

    async for key in storage.list_prefix(prefix):
        path = key[len(prefix) :]
        hash_data = await storage.get(key)
        if hash_data:
            manifest[path] = hash_data.decode()

    return {"case_id": case_id, "files": manifest}


@router.post("/api/studies/{study_id}/cases/{case_id}/check-hashes")
async def check_hashes(
    study_id: str,
    case_id: str,
    hashes: list[str],
) -> dict:
    """Check which hashes already exist in storage (for efficient sync)."""
    storage = get_storage()
    missing = []
    for h in hashes:
        blob_key = f"blobs/{h[:2]}/{h}"
        if not await storage.exists(blob_key):
            missing.append(h)
    return {"missing": missing}
