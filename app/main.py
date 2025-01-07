from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import templates
from app.routes import router
from app.settings import Settings

config = Settings()  # type: ignore[call-arg]

app = FastAPI()
app.mount("/static", StaticFiles(directory=config.static_dir), name="static")

templates.init_app(app, template_dir=config.template_dir)
app.include_router(router)

# Mount the config to the app so we can inject it into requests
app.extra["config"] = config
