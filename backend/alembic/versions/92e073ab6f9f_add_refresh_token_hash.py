"""add refresh token hash

Revision ID: 92e073ab6f9f
Revises: 9f2b7c6a1d3e
Create Date: 2026-06-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "92e073ab6f9f"
down_revision: Union[str, None] = "9f2b7c6a1d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "refresh_token_hash")