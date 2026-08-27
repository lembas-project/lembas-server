from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import close_database
from app.database import init_database
from app.routes import api_router
from app.routes import hidden_router
from app.routes import ui_router
from app.settings import Settings

STATIC_DIR = Path(__file__).parent.parent / "static"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def init_sentry(settings: Settings) -> None:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config: Settings = app.extra["config"]
    await init_database(config)
    yield
    await close_database()


def create_app(config: Settings | None = None) -> FastAPI:
    config = config or Settings()  # type: ignore[call-arg]

    app = FastAPI(
        lifespan=lifespan,
        title="lembas API",
        docs_url=None,
        redoc_url="/api/docs",
    )
    app.include_router(api_router, prefix="/api")
    app.include_router(ui_router)
    app.include_router(hidden_router)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.extra["config"] = config
    app.extra["templates"] = templates

    init_sentry(config)

    return app


app = create_app()
