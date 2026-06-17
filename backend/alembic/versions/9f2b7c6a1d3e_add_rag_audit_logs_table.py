"""add rag_audit_logs table

Revision ID: 9f2b7c6a1d3e
Revises: c0e71c86214f, e7d9f2b3c4a5, add_onboarding_completed_to_users
Create Date: 2026-05-31 00:00:00.000000

Changed: Added the production migration for the RAG audit log table.
Why: Deployments with existing databases need the table before RAG guard
events can be written.
Addresses: Database write failures when prompt-injection, chunk-drop, or
grounding audit events are emitted in production.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b7c6a1d3e"
down_revision: Union[str, Sequence[str], None] = (
    "c0e71c86214f",
    "e7d9f2b3c4a5",
    "add_onboarding_completed_to_users",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reasoning", sa.String(length=1000), nullable=True),
        sa.Column("changes_summary", sa.String(length=1000), nullable=True),
        sa.Column("chunks_total", sa.Integer(), nullable=True),
        sa.Column("chunks_dropped", sa.Integer(), nullable=True),
        sa.Column("grounding_score", sa.Float(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rag_audit_logs_user_id"),
        "rag_audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_audit_logs_event_type"),
        "rag_audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_audit_logs_question_hash"),
        "rag_audit_logs",
        ["question_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_audit_logs_created_at"),
        "rag_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_audit_logs_created_at"), table_name="rag_audit_logs")
    op.drop_index(op.f("ix_rag_audit_logs_question_hash"), table_name="rag_audit_logs")
    op.drop_index(op.f("ix_rag_audit_logs_event_type"), table_name="rag_audit_logs")
    op.drop_index(op.f("ix_rag_audit_logs_user_id"), table_name="rag_audit_logs")
    op.drop_table("rag_audit_logs")
