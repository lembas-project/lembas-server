from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import templates
from app.database import close_database, init_database
from app.routes import router
from app.routes.device_auth import router as device_auth_router
from app.routes.tokens import router as tokens_router
from app.settings import Settings


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

    app = FastAPI(lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=config.static_dir), name="static")

    templates.init_app(app, settings=config)
    app.include_router(router)
    app.include_router(device_auth_router)
    app.include_router(tokens_router)

    # Mount the config to the app so we can inject it into requests
    app.extra["config"] = config

    init_sentry(config)

    return app


app = create_app()
