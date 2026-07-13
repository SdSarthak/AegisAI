"""add token_version to users

Revision ID: d4e5f6a7b8c9
Revises: 0d84589831eb
Create Date: 2026-07-04 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "0d84589831eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
