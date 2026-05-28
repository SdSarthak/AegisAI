"""Add public badge fields

Revision ID: uuid_badge
Revises: eb8060353ac6
Create Date: 2026-05-28 19:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'uuid_badge'
down_revision = 'eb8060353ac6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ai_systems', sa.Column('public_badge_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('ai_systems', sa.Column('public_badge_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_ai_systems_public_badge_id'), 'ai_systems', ['public_badge_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_ai_systems_public_badge_id'), table_name='ai_systems')
    op.drop_column('ai_systems', 'public_badge_id')
    op.drop_column('ai_systems', 'public_badge_enabled')
