"""extend_guard_scan_log_metadata

Revision ID: eb8060353ac6
Revises: 55a49e4b7bc8
Create Date: 2026-05-22 21:44:44.565674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb8060353ac6'
down_revision: Union[str, None] = '55a49e4b7bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to guard_scan_logs
    op.add_column('guard_scan_logs', sa.Column('detection_type', sa.String(length=16), server_default='none', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('regex_flag', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('regex_score', sa.Float(), server_default='0.0', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('intent', sa.String(length=32), server_default='benign', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('ml_confidence', sa.Float(), server_default='0.0', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('combined_score', sa.Float(), server_default='0.0', nullable=False))
    op.add_column('guard_scan_logs', sa.Column('prompt_length', sa.Integer(), nullable=True))
    op.add_column('guard_scan_logs', sa.Column('scanned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    
    # Create index for scanned_at
    op.create_index(op.f('ix_guard_scan_logs_scanned_at'), 'guard_scan_logs', ['scanned_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_guard_scan_logs_scanned_at'), table_name='guard_scan_logs')
    op.drop_column('guard_scan_logs', 'scanned_at')
    op.drop_column('guard_scan_logs', 'prompt_length')
    op.drop_column('guard_scan_logs', 'combined_score')
    op.drop_column('guard_scan_logs', 'ml_confidence')
    op.drop_column('guard_scan_logs', 'intent')
    op.drop_column('guard_scan_logs', 'regex_score')
    op.drop_column('guard_scan_logs', 'regex_flag')
    op.drop_column('guard_scan_logs', 'detection_type')
