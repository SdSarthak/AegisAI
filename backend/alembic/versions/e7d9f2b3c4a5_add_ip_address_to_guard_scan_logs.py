"""add_ip_address_to_guard_scan_logs

Revision ID: e7d9f2b3c4a5
Revises: eb8060353ac6
Create Date: 2026-06-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7d9f2b3c4a5'
down_revision: Union[str, None] = 'eb8060353ac6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('guard_scan_logs', sa.Column('ip_address', sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column('guard_scan_logs', 'ip_address')
