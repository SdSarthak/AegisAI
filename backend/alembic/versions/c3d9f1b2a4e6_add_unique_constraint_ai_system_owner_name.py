"""add unique constraint on ai_systems(owner_id, name)

Revision ID: c3d9f1b2a4e6
Revises: a7c004156ad1
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d9f1b2a4e6'
down_revision: Union[str, None] = 'a7c004156ad1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create composite unique constraint on owner_id, name
    op.create_unique_constraint('uq_ai_system_owner_name', 'ai_systems', ['owner_id', 'name'])


def downgrade() -> None:
    # drop the composite unique constraint
    op.drop_constraint('uq_ai_system_owner_name', 'ai_systems', type_='unique')
