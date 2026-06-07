"""add_ip_address_to_guard_scan_logs

Revision ID: f3a1c9d2b4e7
Revises: eb8060353ac6
Create Date: 2026-05-28 00:00:00.000000

Adds ip_address column to guard_scan_logs for audit trail purposes.
Raw prompt text is intentionally NOT stored — only the SHA-256 hash.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9d2b4e7'
down_revision: Union[str, None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ip_address supports both IPv4 (max 15 chars) and IPv6 (max 45 chars)
    op.add_column(
        'guard_scan_logs',
        sa.Column('ip_address', sa.String(length=45), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('guard_scan_logs', 'ip_address')
