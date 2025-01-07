from contextvars import ContextVar
from typing import Any

import jinja_partials
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app import config

REQUEST_CTX_KEY = "request_id"

_request_ctx_var: ContextVar[Request] = ContextVar(REQUEST_CTX_KEY)

templates = Jinja2Templates(directory=config.template_dir)
jinja_partials.register_starlette_extensions(templates)


def get_request() -> Request:
    return _request_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_ctx_var.set(request)

        response = await call_next(request)

        _request_ctx_var.reset(request_id)

        return response


def render_template(name: str, model: BaseModel | None = None, **context: Any) -> HTMLResponse:
    if model is not None:
        context.update({"model": model.dict(), **model.dict()})
    return templates.TemplateResponse(request=get_request(), name=name, context=context)


def init_app(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
