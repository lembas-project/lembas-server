"""Storage abstraction for artifacts.

Provides a unified interface for storing and retrieving case artifacts,
with implementations for local filesystem (development) and S3-compatible
storage (production).
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

import aioboto3
from botocore.config import Config


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def put(self, key: str, data: bytes) -> str:
        """Store data and return its content hash (SHA-256)."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Retrieve data by key. Returns None if not found."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def list_prefix(self, prefix: str) -> AsyncIterator[str]:
        """List all keys with a given prefix."""
        ...

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Get a URL for accessing the object. Returns None if not supported or not found."""
        ...


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for development."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        return self.base_path / key

    async def put(self, key: str, data: bytes) -> str:
        path = self._key_to_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return compute_hash(data)

    async def get(self, key: str) -> bytes | None:
        path = self._key_to_path(key)
        if not path.exists():
            return None
        return path.read_bytes()

    async def exists(self, key: str) -> bool:
        return self._key_to_path(key).exists()

    async def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if not path.exists():
            return False
        path.unlink()
        return True

    async def list_prefix(self, prefix: str) -> AsyncIterator[str]:
        prefix_path = self._key_to_path(prefix)
        if prefix_path.is_dir():
            for path in prefix_path.rglob("*"):
                if path.is_file():
                    yield str(path.relative_to(self.base_path))
        elif prefix_path.parent.exists():
            for path in prefix_path.parent.glob(f"{prefix_path.name}*"):
                if path.is_file():
                    yield str(path.relative_to(self.base_path))

    async def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        return None


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend for production."""

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        region: str = "auto",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        prefix: str = "",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._session = aioboto3.Session()

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def _get_client_kwargs(self) -> dict:
        kwargs: dict = {
            "service_name": "s3",
            "config": Config(signature_version="s3v4"),
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.region:
            kwargs["region_name"] = self.region
        if self.access_key_id:
            kwargs["aws_access_key_id"] = self.access_key_id
        if self.secret_access_key:
            kwargs["aws_secret_access_key"] = self.secret_access_key
        return kwargs

    async def put(self, key: str, data: bytes) -> str:
        async with self._session.client(**self._get_client_kwargs()) as client:
            await client.put_object(Bucket=self.bucket, Key=self._full_key(key), Body=data)
        return compute_hash(data)

    async def get(self, key: str) -> bytes | None:
        async with self._session.client(**self._get_client_kwargs()) as client:
            try:
                response = await client.get_object(Bucket=self.bucket, Key=self._full_key(key))
                return await response["Body"].read()
            except client.exceptions.NoSuchKey:
                return None

    async def exists(self, key: str) -> bool:
        async with self._session.client(**self._get_client_kwargs()) as client:
            try:
                await client.head_object(Bucket=self.bucket, Key=self._full_key(key))
                return True
            except client.exceptions.ClientError:
                return False

    async def delete(self, key: str) -> bool:
        if not await self.exists(key):
            return False
        async with self._session.client(**self._get_client_kwargs()) as client:
            await client.delete_object(Bucket=self.bucket, Key=self._full_key(key))
        return True

    async def list_prefix(self, prefix: str) -> AsyncIterator[str]:
        full_prefix = self._full_key(prefix)
        async with self._session.client(**self._get_client_kwargs()) as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if self.prefix and key.startswith(self.prefix):
                        key = key[len(self.prefix) :]
                    yield key

    async def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        if not await self.exists(key):
            return None
        async with self._session.client(**self._get_client_kwargs()) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": self._full_key(key)},
                ExpiresIn=expires_in,
            )


def get_storage_backend() -> StorageBackend:
    """Get the configured storage backend based on environment."""
    storage_type = os.environ.get("STORAGE_BACKEND", "local")

    if storage_type == "s3":
        return S3StorageBackend(
            bucket=os.environ["STORAGE_S3_BUCKET"],
            endpoint_url=os.environ.get("STORAGE_S3_ENDPOINT"),
            region=os.environ.get("STORAGE_S3_REGION", "auto"),
            access_key_id=os.environ.get("STORAGE_S3_ACCESS_KEY_ID"),
            secret_access_key=os.environ.get("STORAGE_S3_SECRET_ACCESS_KEY"),
            prefix=os.environ.get("STORAGE_S3_PREFIX", ""),
        )
    else:
        base_path = os.environ.get("STORAGE_LOCAL_PATH", "/data/artifacts")
        return LocalStorageBackend(base_path)


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Get the singleton storage backend instance."""
    global _storage
    if _storage is None:
        _storage = get_storage_backend()
    return _storage
