"""Application configuration."""

from urllib.parse import urlencode

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    client_id: str
    client_secret: str
    redirect_url: str = "http://lembas.localhost"
    token_url: str = "https://github.com/login/oauth/access_token"
    login_url_base: str = "https://github.com/login/oauth/authorize"

    static_dir: str = "static"
    template_dir: str = "templates"

    @property
    def login_url(self) -> str:
        login_url = (
            self.login_url_base
            + "?"
            + urlencode(dict(client_id=self.client_id, redirect_url=self.redirect_url))
        )
        return login_url
