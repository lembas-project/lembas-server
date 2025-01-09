from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.templates import render_template


class Component(BaseModel):
    __template_path__ = ""
    __template__ = ""

    def render(self) -> HTMLResponse:
        # We do a shallow dump to prevent serializing every nested thing into a dictionary
        shallow_dump = {name: getattr(self, name) for name in self.model_fields.keys()}
        # TODO: Passing in Button should be done via some type of registration process instead
        return render_template(self.__template_path__, **shallow_dump, Button=Button)


class Button(Component):
    __template__ = """
      <button
        class="button-link px-6 py-3 bg-green-500 hover:bg-green-600 text-white
               font-semibold rounded-lg transition duration-300 ease-in-out
               transform hover:scale-105"
        data-href="{{ url }}"
      >
        <a href="{{ url }}">{{ text }}</a>
      </button>
      """
    url: str = ""
    text: str = ""


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
