"""add dashboard layout to users

Revision ID: 0d84589831eb
Revises: 9f2b7c6a1d3e
Create Date: 2026-06-19 21:28:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0d84589831eb"
down_revision = "9f2b7c6a1d3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("dashboard_layout", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "dashboard_layout")