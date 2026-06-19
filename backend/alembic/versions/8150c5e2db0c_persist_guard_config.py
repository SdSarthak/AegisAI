"""persist guard config

Revision ID: 8150c5e2db0c
Revises: 9f2b7c6a1d3e
Create Date: 2026-06-19 12:26:18.219525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8150c5e2db0c"
down_revision: Union[str, None] = "9f2b7c6a1d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("guard_sanitization_level", sa.String(length=20), nullable=False, server_default="medium"),
    )
    op.add_column(
        "users",
        sa.Column("guard_malicious_threshold", sa.Float(), nullable=False, server_default="0.8"),
    )
    op.add_column(
        "users",
        sa.Column("guard_suspicious_threshold", sa.Float(), nullable=False, server_default="0.5"),
    )


def downgrade() -> None:
    op.drop_column("users", "guard_suspicious_threshold")
    op.drop_column("users", "guard_malicious_threshold")
    op.drop_column("users", "guard_sanitization_level")