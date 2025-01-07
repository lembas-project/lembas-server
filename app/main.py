from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config, templates
from app.routes import router

app = FastAPI()
app.mount("/static", StaticFiles(directory=config.static_dir), name="static")

templates.init_app(app)
app.include_router(router)
