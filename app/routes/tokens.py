"""Token management API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.models import User as DBUser
from app.dependencies import require_db_user
from app.services.token_service import create_token, list_user_tokens, revoke_token

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class TokenInfo(BaseModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class TokenListResponse(BaseModel):
    tokens: list[TokenInfo]


class CreateTokenRequest(BaseModel):
    name: str
    expires_in_days: int | None = 90


class CreateTokenResponse(BaseModel):
    token: str
    id: int
    name: str
    expires_at: datetime | None


@router.get("")
async def list_tokens(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[DBUser, Depends(require_db_user)],
) -> TokenListResponse:
    """List all API tokens for the authenticated user."""
    tokens = await list_user_tokens(db, user.id)
    return TokenListResponse(
        tokens=[
            TokenInfo(
                id=t.id,
                name=t.name,
                prefix=t.token_prefix,
                created_at=t.created_at,
                expires_at=t.expires_at,
                last_used_at=t.last_used_at,
            )
            for t in tokens
        ]
    )


@router.post("")
async def create_new_token(
    body: CreateTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[DBUser, Depends(require_db_user)],
) -> CreateTokenResponse:
    """Create a new API token."""
    token, api_token = await create_token(
        db,
        user_id=user.id,
        name=body.name,
        expires_days=body.expires_in_days,
    )
    return CreateTokenResponse(
        token=token,
        id=api_token.id,
        name=api_token.name,
        expires_at=api_token.expires_at,
    )


@router.delete("/{token_id}")
async def delete_token(
    token_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[DBUser, Depends(require_db_user)],
) -> dict[str, str]:
    """Revoke an API token."""
    success = await revoke_token(db, user.id, token_id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "ok"}
