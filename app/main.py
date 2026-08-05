import sentry_sdk
from fastapi import FastAPI

from app.routes import router
from app.settings import Settings


def init_sentry(settings: Settings) -> None:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release,
    )


def create_app(config: Settings | None = None) -> FastAPI:
    config = config or Settings()  # type: ignore[call-arg]

    app = FastAPI()
    app.include_router(router)

    app.extra["config"] = config

    init_sentry(config)

    return app


app = create_app()
