"""add_webhook_configs_table

Revision ID: 55a49e4b7bc8
Revises: 
Create Date: 2026-05-15 02:29:34.617011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '55a49e4b7bc8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'webhook_configs' not in inspector.get_table_names():
        op.create_table(
            'webhook_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('url', sa.String(length=1000), nullable=False),
            sa.Column('secret', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('events', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    op.create_index(
        op.f('ix_webhook_configs_id'),
        'webhook_configs',
<<<<<<< HEAD
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('events', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
=======
        ['id'],
        unique=False,
>>>>>>> 0e31294 (fix: make alembic table migrations idempotent)
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_webhook_configs_id'), table_name='webhook_configs')
    op.drop_table('webhook_configs')
