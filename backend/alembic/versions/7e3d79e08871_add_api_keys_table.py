"""add api_keys table

Revision ID: 7e3d79e08871
Revises: eb8060353ac6
Create Date: 2026-05-28 19:29:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e3d79e08871"
down_revision: Union[str, None] = "eb8060353ac6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_api_keys_id"),
        "api_keys",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_api_keys_key_hash"),
        "api_keys",
        ["key_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_api_keys_key_hash"),
        table_name="api_keys",
    )

    op.drop_index(
        op.f("ix_api_keys_id"),
        table_name="api_keys",
    )

    op.drop_table("api_keys")