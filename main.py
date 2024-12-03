import hashlib
import json
from contextvars import ContextVar
from typing import Annotated

import jinja_partials
from fastapi import FastAPI, Form, Header, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, computed_field
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


def render_template(name, model: BaseModel | None = None):
    context = {"model": model.dict(), **model.dict()} if model is not None else {}
    return templates.TemplateResponse(request=get_request(), name=name, context=context)


@app.get("/")
async def home() -> HTMLResponse:
    with open("templates/index.html", "rb") as fp:
        return HTMLResponse(content=fp.read(), media_type="text/html", status_code=200)


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


try:
    with open("repodata.json") as fp:
        data = json.load(fp)
except FileNotFoundError:
    data = {}

packages = data.get("packages", [])
package_names = sorted(set(p["name"] for filename, p in packages.items()))

PAGE_SIZE = 10


class ChannelListModel(BaseModel):
    packages: list[str] = []
    page: int = 1


@app.get("/app/main")
async def main_channel(
    from_htmx: Annotated[str, Header(alias="hx-request")] = "",
    page: int = 1,
) -> ChannelListModel:
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    model = ChannelListModel(packages=package_names[start:end], page=page)
    if from_htmx:
        return render_template("partials/package_table.html", model=model)
    return render_template("channel_list.html", model=model)


@app.get("/app")
async def app_home():
    return render_template("app.html")


class AccountProfileViewModel(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""

    @computed_field
    @property
    def gravitar_url(self) -> str:
        email_hash = hashlib.md5(self.email.strip().lower().encode("utf-8")).hexdigest()
        gravitar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
        return gravitar_url


ACCOUNT_DATABASE = {}
USER_ID = "mrk"


@app.get("/app/profile/account-settings")
async def account_settings(from_htmx: Annotated[str, Header(alias="hx-request")] = ""):
    model = AccountProfileViewModel(**ACCOUNT_DATABASE.get(USER_ID, {}))
    if from_htmx:
        return render_template("partials/account-settings-form.html", model=model)
    return render_template(
        "account-settings.html",
        model=model,
    )


@app.put("/app/profile/account-settings")
async def update_account_settings(
    first_name: Annotated[str, Form()] = "",
    last_name: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
):
    ACCOUNT_DATABASE[USER_ID] = {"first_name": first_name, "last_name": last_name, "email": email}
    model = AccountProfileViewModel(**ACCOUNT_DATABASE.get(USER_ID, {}))
    return render_template("partials/account-settings-form.html", model=model)
