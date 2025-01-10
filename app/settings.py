"""Application configuration."""

from urllib.parse import urlencode

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    live_reload_mode: bool = False

    client_id: str
    client_secret: str
    redirect_url: str = "http://lembas.localhost"
    token_url: str = "https://github.com/login/oauth/access_token"
    login_url_base: str = "https://github.com/login/oauth/authorize"

    static_dir: str = "static"
    template_dir: str = "templates"

    sentry_dsn: str = ""
    sentry_environment: str = "dev"
    sentry_release: str = "unknown"

    @property
    def login_url(self) -> str:
        login_url = (
            self.login_url_base
            + "?"
            + urlencode(dict(client_id=self.client_id, redirect_url=self.redirect_url))
        )
        return login_url
