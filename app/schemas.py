from pydantic import BaseModel


class User(BaseModel):
    """User schema for API responses."""

    username: str
    name: str | None = None
    avatar_url: str = ""
