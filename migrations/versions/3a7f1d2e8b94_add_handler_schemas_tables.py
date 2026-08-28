"""Add handler_schemas and study_handler_schemas tables

Revision ID: 3a7f1d2e8b94
Revises: 85422e178f21
Create Date: 2026-08-28 10:00:00.000000

Adds a content-addressed handler schema registry. Schemas are stored
once per fingerprint and linked to studies via a join table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3a7f1d2e8b94"
down_revision: str | Sequence[str] | None = "85422e178f21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "handler_schemas",
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schema_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("fingerprint"),
    )
    op.create_index(op.f("ix_handler_schemas_name"), "handler_schemas", ["name"], unique=False)
    op.create_table(
        "study_handler_schemas",
        sa.Column("study_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["fingerprint"], ["handler_schemas.fingerprint"]),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"]),
        sa.PrimaryKeyConstraint("study_id", "fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("study_handler_schemas")
    op.drop_index(op.f("ix_handler_schemas_name"), table_name="handler_schemas")
    op.drop_table("handler_schemas")
