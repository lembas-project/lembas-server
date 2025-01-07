from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import templates
from app.routes import router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates.init_app(app)
app.include_router(router)
