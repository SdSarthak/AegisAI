"""add guard_audit_logs table for compliance audit trail

Revision ID: f8e2a1b3c5d7
Revises: c3d9f1b2a4e6
Create Date: 2026-06-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e2a1b3c5d7'
down_revision: Union[str, None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'guard_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False),
        sa.Column('decision', sa.String(length=16), nullable=False),
        sa.Column('threat_type', sa.String(length=32), nullable=False, server_default='none'),
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
