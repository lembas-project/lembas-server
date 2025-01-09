from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.templates import render_template


class Component(BaseModel):
    __template_path__ = ""

    def render(self) -> HTMLResponse:
        # We do a shallow dump to prevent serializing every nested thing into a dictionary
        shallow_dump = {name: getattr(self, name) for name in self.model_fields.keys()}
        return render_template(self.__template_path__, **shallow_dump)


class User(Component):
    __template_path__ = "partials/user.html"

    username: str = Field(validation_alias="login")
    name: str | None = None
    avatar_url: str = ""


class Homepage(Component):
    __template_path__ = "home.html"

    user: User | None
    login_url: str
    logout_url: str
    projects: list = []
