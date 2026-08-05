from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from app.database import close_database, init_database
from app.routes import router
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
    app.include_router(router)

    app.extra["config"] = config

    init_sentry(config)

    return app


app = create_app()
