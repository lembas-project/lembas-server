"""Add studies and cases tables

Revision ID: b933dc56a3e2
Revises: 742059394c24
Create Date: 2026-08-25 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b933dc56a3e2"
down_revision: str | Sequence[str] | None = "742059394c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "studies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("plugins_declared", sa.Text(), nullable=True),
        sa.Column("handlers", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("pushed_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("study_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("handler_fqn", sa.Text(), nullable=False),
        sa.Column("inputs", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("environment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cases_study_id"), "cases", ["study_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cases_study_id"), table_name="cases")
    op.drop_table("cases")
    op.drop_table("studies")
