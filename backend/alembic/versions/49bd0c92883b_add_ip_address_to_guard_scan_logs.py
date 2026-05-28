"""add_ip_address_to_guard_scan_logs

Revision ID: 49bd0c92883b
Revises: c3d9f1b2a4e6
Create Date: 2026-05-29 00:03:50.797617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49bd0c92883b'
down_revision: Union[str, None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('guard_scan_logs', sa.Column('ip_address', sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column('guard_scan_logs', 'ip_address')

