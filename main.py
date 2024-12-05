import logging
import os
from contextvars import ContextVar
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import jinja_partials
from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

load_dotenv()

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDIRECT_URL = os.environ["REDIRECT_URL"]
TOKEN_URL = os.environ["TOKEN_URL"]
LOGIN_URL_BASE = os.environ["LOGIN_URL_BASE"]
LOGIN_URL = LOGIN_URL_BASE + "?" + urlencode(dict(client_id=CLIENT_ID, redirect_url=REDIRECT_URL))

log = logging.getLogger(__name__)

templates = Jinja2Templates("tests/test_templates")

REQUEST_CTX_KEY = "request_id"

_request_ctx_var: ContextVar[Request] = ContextVar(REQUEST_CTX_KEY)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
jinja_partials.register_starlette_extensions(templates)


def get_request() -> Request:
    return _request_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_ctx_var.set(request)

        response = await call_next(request)

        _request_ctx_var.reset(request_id)

        return response


app.add_middleware(RequestContextMiddleware)


def render_template(name: str, model: BaseModel | None = None, **context: Any) -> HTMLResponse:
    if model is not None:
        context.update({"model": model.dict(), **model.dict()})
    return templates.TemplateResponse(request=get_request(), name=name, context=context)


@app.get("/")
async def home(access_token: Annotated[str | None, Cookie()] = None) -> HTMLResponse:
    return render_template(
        "home.html",
        projects=[{"name": "project 1"}],
        login_url=LOGIN_URL,
        # TODO: Use request.url_for
        logout_url="/auth/logout",
        access_token=access_token,
    )


@app.get("/auth/callback")
async def auth_callback(code: str) -> RedirectResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            json=dict(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                code=code,
                redirect_url=REDIRECT_URL,
            ),
            headers={
                "Accept": "application/json",
            },
        )
    # TODO: Add Error handling for non-200 responses
    data = resp.json()
    access_token = data["access_token"]

    response = RedirectResponse("/")
    response.set_cookie(key="access_token", value=access_token)
    return response


@app.get("/auth/logout")
async def auth_logout() -> RedirectResponse:
    # TODO: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-token
    response = RedirectResponse("/")
    response.delete_cookie(key="access_token")
    return response


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}
