"""Rename api_tokens.token to token_hash

Revision ID: 85422e178f21
Revises: c4e1a7f92b83
Create Date: 2026-08-27 11:05:00.000000

The token column previously stored raw token values. After the security
fix it stores SHA-256 hashes. This migration renames the column to
token_hash to make that explicit.

Note: SQLite does not support ALTER COLUMN, so this uses a table rebuild.
The table is empty at this point (cleared by c4e1a7f92b83) so no data
migration is needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "85422e178f21"
down_revision: str | Sequence[str] | None = "c4e1a7f92b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN RENAME, so recreate the table.
    # The table is guaranteed empty at this point (cleared by c4e1a7f92b83).
    op.create_table(
        "api_tokens_new",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_tokens_token_hash", "api_tokens_new", ["token_hash"], unique=True)
    op.create_index("ix_api_tokens_new_user_id", "api_tokens_new", ["user_id"], unique=False)

    op.drop_index("ix_api_tokens_token", table_name="api_tokens")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
    op.rename_table("api_tokens_new", "api_tokens")
    op.execute("DROP INDEX IF EXISTS ix_api_tokens_new_user_id")
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.create_table(
        "api_tokens_old",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_tokens_token", "api_tokens_old", ["token"], unique=True)
    op.create_index("ix_api_tokens_old_user_id", "api_tokens_old", ["user_id"], unique=False)

    op.drop_index("ix_api_tokens_token_hash", table_name="api_tokens")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
    op.rename_table("api_tokens_old", "api_tokens")
    op.execute("DROP INDEX IF EXISTS ix_api_tokens_old_user_id")
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"], unique=False)
