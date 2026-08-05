"""Cryptographic utilities for token generation and hashing."""

import hashlib
import secrets
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet

TOKEN_PREFIX = "lb_v1_"
USER_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_api_token() -> tuple[str, str]:
    """Generate a new API token.

    Returns:
        Tuple of (full_token, token_hash) where full_token is shown to user once
        and token_hash is stored in database.
    """
    random_bytes = secrets.token_bytes(32)
    token = TOKEN_PREFIX + urlsafe_b64encode(random_bytes).decode().rstrip("=")
    token_hash = hash_token(token)
    return token, token_hash


def hash_token(token: str) -> str:
    """Hash a token for storage/lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_device_code() -> str:
    """Generate a random device code."""
    return secrets.token_urlsafe(32)


def generate_user_code() -> str:
    """Generate a human-readable user code like LMBS-XXXX."""
    code = "".join(secrets.choice(USER_CODE_CHARS) for _ in range(4))
    return f"LMBS-{code}"


def get_token_prefix(token: str) -> str:
    """Extract a prefix from a token for identification."""
    return token[:12] if len(token) >= 12 else token


def encrypt_value(value: str, key: str) -> str:
    """Encrypt a value using Fernet symmetric encryption."""
    if not key:
        return value
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str, key: str) -> str:
    """Decrypt a value using Fernet symmetric encryption."""
    if not key:
        return encrypted
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    return f.decrypt(encrypted.encode()).decode()


def _derive_fernet_key(key: str) -> bytes:
    """Derive a Fernet-compatible key from an arbitrary string."""
    digest = hashlib.sha256(key.encode()).digest()
    return urlsafe_b64encode(digest)
