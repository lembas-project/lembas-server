from pydantic import BaseModel


class User(BaseModel):
    """User schema for API responses."""

    username: str
    avatar_url: str = ""
