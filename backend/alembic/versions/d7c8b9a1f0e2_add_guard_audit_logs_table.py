"""add_guard_audit_logs_table

Revision ID: d7c8b9a1f0e2
Revises: eb8060353ac6
Create Date: 2026-05-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7c8b9a1f0e2'
down_revision: Union[str, None] = 'eb8060353ac6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'guard_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False),
        sa.Column('decision', sa.String(length=16), nullable=False),
        sa.Column('threat_type', sa.String(length=32), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_guard_audit_logs_id'), 'guard_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_guard_audit_logs_user_id'), 'guard_audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_guard_audit_logs_timestamp'), 'guard_audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_guard_audit_logs_timestamp'), table_name='guard_audit_logs')
    op.drop_index(op.f('ix_guard_audit_logs_user_id'), table_name='guard_audit_logs')
    op.drop_index(op.f('ix_guard_audit_logs_id'), table_name='guard_audit_logs')
    op.drop_table('guard_audit_logs')
