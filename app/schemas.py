from pydantic import BaseModel, Field


class User(BaseModel):
    """User schema for API responses."""

    username: str = Field(alias="login", serialization_alias="username")
    name: str | None = None
    avatar_url: str = ""
