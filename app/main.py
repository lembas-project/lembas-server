import sentry_sdk
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import templates
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
    app.mount("/static", StaticFiles(directory=config.static_dir), name="static")

    templates.init_app(app, template_dir=config.template_dir)
    app.include_router(router)

    # Mount the config to the app so we can inject it into requests
    app.extra["config"] = config

    init_sentry(config)

    return app


app = create_app()
