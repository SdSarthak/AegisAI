"""merge multiple heads

Revision ID: 2e99a49f711a
Revises: 4d8e9f0a1b2c, a1b2c3d4e5f6, d4e5f6a7b8c9
Create Date: 2026-07-13 07:14:33.635133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e99a49f711a'
down_revision: Union[str, None] = ('4d8e9f0a1b2c', 'a1b2c3d4e5f6', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
