"""add_public_badge_fields_to_ai_systems

Revision ID: 696ab9f08d10
Revises: c3d9f1b2a4e6
Create Date: 2026-05-31 20:21:25.914380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '696ab9f08d10'
down_revision: Union[str, None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ai_systems', sa.Column('public_badge_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('ai_systems', sa.Column('public_badge_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_ai_systems_public_badge_id'), 'ai_systems', ['public_badge_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_systems_public_badge_id'), table_name='ai_systems')
    op.drop_column('ai_systems', 'public_badge_id')
    op.drop_column('ai_systems', 'public_badge_enabled')
