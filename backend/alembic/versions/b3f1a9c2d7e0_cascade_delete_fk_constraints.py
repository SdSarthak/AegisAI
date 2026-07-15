"""add ondelete CASCADE/SET NULL to FK constraints for user and ai_system deletion

Revision ID: b3f1a9c2d7e0
Revises: a1b2c3d4e5f6, d4e5f6a7b8c9
Create Date: 2026-07-15 00:00:00.000000

Merges the two current heads and applies the DB-level ondelete actions
that back PR #1507 / issue #1436.

Audit and log tables (ai_system_audit_logs.changed_by_id, rag_audit_logs.user_id,
guard_scan_logs.user_id) use SET NULL rather than CASCADE so compliance and
security records survive deletion of the user they reference, per review
feedback on #1507. Everything else (a user's own AI systems, documents,
webhook configs, notifications, and an AI system's own risk assessments,
documents, compliance snapshots, and audit trail) uses CASCADE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1a9c2d7e0'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, referenced_table, ondelete)
_CASCADE_FKS = [
    ("ai_systems", "owner_id", "users", "CASCADE"),
    ("risk_assessments", "ai_system_id", "ai_systems", "CASCADE"),
    ("documents", "owner_id", "users", "CASCADE"),
    ("documents", "ai_system_id", "ai_systems", "CASCADE"),
    ("document_versions", "document_id", "documents", "CASCADE"),
    ("compliance_snapshots", "ai_system_id", "ai_systems", "CASCADE"),
    ("notifications", "user_id", "users", "CASCADE"),
    ("webhook_configs", "user_id", "users", "CASCADE"),
    ("rag_queries", "user_id", "users", "CASCADE"),
    ("ai_system_audit_logs", "ai_system_id", "ai_systems", "CASCADE"),
]

# (table, column, referenced_table) — SET NULL, column also made nullable
_SET_NULL_FKS = [
    ("ai_system_audit_logs", "changed_by_id", "users"),
    ("rag_audit_logs", "user_id", "users"),
    ("guard_scan_logs", "user_id", "users"),
]


def upgrade() -> None:
    for table, column, ref_table, ondelete in _CASCADE_FKS:
        constraint_name = f"{table}_{column}_fkey"
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name, table, ref_table, [column], ["id"], ondelete=ondelete
        )

    for table, column, ref_table in _SET_NULL_FKS:
        constraint_name = f"{table}_{column}_fkey"
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=True)
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name, table, ref_table, [column], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    for table, column, ref_table in _SET_NULL_FKS:
        constraint_name = f"{table}_{column}_fkey"
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, ref_table, [column], ["id"])

    # rag_audit_logs.user_id and guard_scan_logs.user_id were already/now
    # nullable=False before this migration except rag_audit_logs, which was
    # already nullable=True beforehand — only restore guard_scan_logs and
    # ai_system_audit_logs.changed_by_id back to NOT NULL.
    op.alter_column("guard_scan_logs", "user_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("ai_system_audit_logs", "changed_by_id", existing_type=sa.Integer(), nullable=False)

    for table, column, ref_table, _ondelete in _CASCADE_FKS:
        constraint_name = f"{table}_{column}_fkey"
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, ref_table, [column], ["id"])
