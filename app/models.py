from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.templates import render_template


class User(BaseModel):
    username: str = Field(validation_alias="login")
    name: str | None = None
    avatar_url: str = ""


class Component(BaseModel):
    __template_path__ = ""
    __template__ = ""

    def render(self) -> HTMLResponse:
        # We do a shallow dump to prevent serializing every nested thing into a dictionary
        shallow_dump = {name: getattr(self, name) for name in self.model_fields.keys()}
        # TODO: Passing in Button should be done via some type of registration process instead
        return render_template(
            self.__template_path__, **shallow_dump, LinkButton=LinkButton, UserCard=UserCard
        )


class LinkButton(Component):
    __template_path__ = "partials/link_button.html"

    url: str = ""
    text: str = ""


class UserCard(Component):
    __template_path__ = "partials/user_card.html"

    user: User | None


class Homepage(Component):
    __template_path__ = "home.html"

    user: User | None
    login_url: str
    logout_url: str
    projects: list = []
