from contextvars import ContextVar
from typing import Any

import jinja_partials
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

templates = Jinja2Templates("tests/test_templates")

REQUEST_CTX_KEY = "request_id"

_request_ctx_var: ContextVar[Request] = ContextVar(REQUEST_CTX_KEY, default=None)

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


def render_template(name, model: BaseModel | None = None, **context: Any):
    if model is not None:
        context.update({"model": model.dict(), **model.dict()})
    return templates.TemplateResponse(request=get_request(), name=name, context=context)


@app.get("/")
async def home() -> HTMLResponse:
    return render_template("home.html", projects=[{"name": "project 1"}])


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}
