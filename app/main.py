from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import templates
from app.routes import router
from app.settings import Settings

config = Settings()  # type: ignore[call-arg]

app = FastAPI()
app.mount("/static", StaticFiles(directory=config.static_dir), name="static")

templates.init_app(app)
app.include_router(router)
