"""remove_guard_audit_logs_table

Revision ID: f1a2b3c4d5e6
Revises: eb8060353ac6
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'eb8060353ac6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop indexes and table used for legacy guard audit logs
    try:
        op.drop_index(op.f('ix_guard_audit_logs_timestamp'), table_name='guard_audit_logs')
    except Exception:
        pass

    try:
        op.drop_index(op.f('ix_guard_audit_logs_user_id'), table_name='guard_audit_logs')
    except Exception:
        pass

    try:
        op.drop_index(op.f('ix_guard_audit_logs_id'), table_name='guard_audit_logs')
    except Exception:
        pass

    # Drop the table if it exists
    op.drop_table('guard_audit_logs')


def downgrade() -> None:
    # Recreate the guard_audit_logs table (reverse of the removed migration)
    op.create_table(
        'guard_audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('decision', sa.String(length=16), nullable=False),
        sa.Column('threat_type', sa.String(length=32), nullable=False, server_default='unknown'),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
    )
    op.create_index(op.f('ix_guard_audit_logs_id'), 'guard_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_guard_audit_logs_user_id'), 'guard_audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_guard_audit_logs_timestamp'), 'guard_audit_logs', ['timestamp'], unique=False)
