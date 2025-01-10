from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, Template
from jinja2.ext import Extension
from markupsafe import Markup
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates


REQUEST_CTX_KEY = "request_id"

_request_ctx_var: ContextVar[Request] = ContextVar(REQUEST_CTX_KEY)

templates: Jinja2Templates | None = None


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

    if templates is None:
        raise ValueError("Template engine never initialized")

    return templates.TemplateResponse(request=get_request(), name=name, context=context)


class AutoRenderExtension(Extension):
    """An extension to automatically render a pydantic model."""

    def __init__(self, environment: Environment):
        super().__init__(environment)

        # Add the filter to the environment
        environment.filters["auto_render"] = self.auto_render_filter

        # Override the default finalize function
        environment.finalize = self.auto_render_filter

    def auto_render_filter(self, obj: Any) -> Any:
        from app.components import Component

        if isinstance(obj, Component):
            if p := obj.__template_path__:
                if templates is None:
                    raise ValueError("Template engine never initialized")
                template = templates.get_template(p)
            elif t := obj.__template__:
                template = Template(t)
            else:
                return obj
            return Markup(template.render(**obj.model_dump()))
        return obj


def render_partial(
    template_name: str,
    markup: bool = True,
    **data: Any,
) -> Markup | str:
    if templates is None:
        raise ValueError("Template engine never initialized")

    content = templates.get_template(template_name).render(**data)
    if markup:
        return Markup(content)
    return content


def init_app(app: FastAPI, template_dir: str) -> None:
    global templates

    templates = Jinja2Templates(directory=template_dir)
    templates.env.add_extension(AutoRenderExtension)
    templates.env.globals.update(render_partial=render_partial)

    app.add_middleware(RequestContextMiddleware)
