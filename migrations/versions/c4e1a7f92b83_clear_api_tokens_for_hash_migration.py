"""Clear api_tokens table for hash migration

Revision ID: c4e1a7f92b83
Revises: f3a1c9e82d07
Create Date: 2026-08-27 10:40:00.000000

Existing tokens were stored as raw values. After this migration tokens are
stored as SHA-256 hashes. All existing tokens are invalidated — users must
run `lembas auth login` again to obtain a new token.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e1a7f92b83"
down_revision: str | Sequence[str] | None = "f3a1c9e82d07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM api_tokens")


def downgrade() -> None:
    # Tokens cannot be un-hashed; downgrade just leaves the table empty.
    pass
