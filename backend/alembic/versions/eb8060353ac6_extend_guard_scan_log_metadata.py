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


def _column_exists(table_name: str, column_name: str) -> bool:
    """Return True if the column already exists in the table."""
    bind = op.get_context().bind
    inspector = sa.inspect(bind)
    return column_name in [c["name"] for c in inspector.get_columns(table_name)]


_COLUMNS = [
    ("detection_type", sa.Column("detection_type", sa.String(length=16), server_default="none", nullable=False)),
    ("regex_flag", sa.Column("regex_flag", sa.Boolean(), server_default="false", nullable=False)),
    ("regex_score", sa.Column("regex_score", sa.Float(), server_default="0.0", nullable=False)),
    ("intent", sa.Column("intent", sa.String(length=32), server_default="benign", nullable=False)),
    ("ml_confidence", sa.Column("ml_confidence", sa.Float(), server_default="0.0", nullable=False)),
    ("combined_score", sa.Column("combined_score", sa.Float(), server_default="0.0", nullable=False)),
    ("prompt_length", sa.Column("prompt_length", sa.Integer(), nullable=True)),
    ("scanned_at", sa.Column("scanned_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False)),
]


def upgrade() -> None:
    table = "guard_scan_logs"
    for col_name, col_def in _COLUMNS:
        if not _column_exists(table, col_name):
            op.add_column(table, col_def)

    if not _column_exists(table, "scanned_at"):
        op.create_index(op.f("ix_guard_scan_logs_scanned_at"), table, ["scanned_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_guard_scan_logs_scanned_at"), table_name="guard_scan_logs")
    op.drop_column("guard_scan_logs", "scanned_at")
    op.drop_column("guard_scan_logs", "prompt_length")
    op.drop_column("guard_scan_logs", "combined_score")
    op.drop_column("guard_scan_logs", "ml_confidence")
    op.drop_column("guard_scan_logs", "intent")
    op.drop_column("guard_scan_logs", "regex_score")
    op.drop_column("guard_scan_logs", "regex_flag")
    op.drop_column("guard_scan_logs", "detection_type")
