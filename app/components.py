from typing import Any

from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.datastructures import URL

from app.models import User
from app.templates import render_template


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

    user: User


class URLString(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, *_) -> str:
        if isinstance(v, URL):
            return str(v)
        elif isinstance(v, str):
            return v
        raise ValueError(f"Invalid URL: {v}")


class Homepage(Component):
    __template_path__ = "home.html"

    user: User | None
    login_url: URLString
    logout_url: URLString
    projects: list = []
