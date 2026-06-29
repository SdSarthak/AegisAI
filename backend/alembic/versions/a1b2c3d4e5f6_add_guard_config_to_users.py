"""add guard config columns to users

Revision ID: a1b2c3d4e5f6
Revises: 0d84589831eb
Create Date: 2026-06-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "0d84589831eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("guard_sanitization_level", sa.String(10), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("guard_malicious_threshold", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("guard_suspicious_threshold", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "guard_suspicious_threshold")
    op.drop_column("users", "guard_malicious_threshold")
    op.drop_column("users", "guard_sanitization_level")
