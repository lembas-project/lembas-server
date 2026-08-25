"""Change User.id to UUID primary key, store github_id as string

Revision ID: ee252c2d7beb
Revises: 742059394c24
Create Date: 2026-08-25 12:30:00.000000

Migrates the users table id column from Integer to Uuid and
github_id from Integer to String.

Note: SQLite does not support ALTER COLUMN, so this migration recreates
the users table with the new schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ee252c2d7beb"
down_revision: str | Sequence[str] | None = "742059394c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Recreate users table with Uuid PK (SQLite does not support ALTER COLUMN)
    op.create_table(
        "users_new",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("github_id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_new_github_id"), "users_new", ["github_id"], unique=True)

    # Copy existing rows, generating UUIDs for the new id column
    op.execute(
        "INSERT INTO users_new (id, github_id, username, avatar_url, created_at, updated_at) "
        "SELECT lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || "
        "       substr(lower(hex(randomblob(2))),2) || '-' || "
        "       substr('89ab', abs(random()) % 4 + 1, 1) || "
        "       substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))), "
        "       CAST(github_id AS TEXT), username, avatar_url, created_at, updated_at "
        "FROM users"
    )

    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_table("users")
    op.rename_table("users_new", "users")
    op.execute("DROP INDEX IF EXISTS ix_users_new_github_id")
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)


def downgrade() -> None:
    op.create_table(
        "users_old",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_old_github_id"), "users_old", ["github_id"], unique=True)

    op.execute(
        "INSERT INTO users_old (github_id, username, avatar_url, created_at, updated_at) "
        "SELECT CAST(github_id AS INTEGER), username, avatar_url, created_at, updated_at "
        "FROM users"
    )

    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_table("users")
    op.rename_table("users_old", "users")
    op.execute("DROP INDEX IF EXISTS ix_users_old_github_id")
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)
