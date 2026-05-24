"""add_user_integrations_table

Revision ID: 137b8187e377
Revises: 55a49e4b7bc8
Create Date: 2026-05-24 19:23:05.102279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '137b8187e377'
down_revision: Union[str, None] = '55a49e4b7bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    integration_type = postgresql.ENUM('jira', 'linear', name='integrationtype', create_type=False)
    op.create_table(
        'user_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('integration_type', integration_type, nullable=False),
        sa.Column('base_url', sa.String(512), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('api_token', sa.String(512), nullable=False),
        sa.Column('project_key', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_integrations_id'), 'user_integrations', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_integrations_id'), table_name='user_integrations')
    op.drop_table('user_integrations')