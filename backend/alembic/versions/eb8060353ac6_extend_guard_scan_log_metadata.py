"""extend_guard_scan_log_metadata

Revision ID: eb8060353ac6
Revises: 55a49e4b7bc8
Create Date: 2026-05-22 21:44:44.565674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb8060353ac6'
down_revision: Union[str, None] = '55a49e4b7bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    

def downgrade() -> None:
    pass