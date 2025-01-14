from pydantic import BaseModel, Field


class User(BaseModel):
    username: str = Field(validation_alias="login")
    name: str | None = None
    avatar_url: str = ""


class Project(BaseModel):
    id: int | None = None
    name: str
