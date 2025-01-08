from pydantic import BaseModel, Field


class User(BaseModel):
    __template_path__ = "partials/user.html"

    username: str = Field(validation_alias="login")
    name: str | None = None
    avatar_url: str = ""
