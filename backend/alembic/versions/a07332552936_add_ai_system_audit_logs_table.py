"""add ai_system_audit_logs table

Revision ID: a07332552936
Revises: 
Create Date: 2026-05-10 21:44:14.183048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a07332552936'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_system_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ai_system_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ai_system_id'], ['ai_systems.id']),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_system_audit_logs_id', 'ai_system_audit_logs', ['id'])


def downgrade() -> None:
    op.drop_index('ix_ai_system_audit_logs_id', table_name='ai_system_audit_logs')
    op.drop_table('ai_system_audit_logs')


