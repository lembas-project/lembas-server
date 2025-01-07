"""Application configuration."""

import os
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

# TODO: Implement proper settings class
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDIRECT_URL = os.getenv("REDIRECT_URL", "http://lembas.localhost")
TOKEN_URL = os.getenv("TOKEN_URL", "https://github.com/login/oauth/access_token")
LOGIN_URL_BASE = os.getenv("LOGIN_URL_BASE", "https://github.com/login/oauth/authorize")
LOGIN_URL = LOGIN_URL_BASE + "?" + urlencode(dict(client_id=CLIENT_ID, redirect_url=REDIRECT_URL))

static_dir = "static"
template_dir = "templates"
