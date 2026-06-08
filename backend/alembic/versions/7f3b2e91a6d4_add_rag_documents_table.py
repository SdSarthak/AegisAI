"""add_rag_documents_table

Revision ID: 7f3b2e91a6d4
Revises: add_onboarding_completed_to_users, c0e71c86214f, e7d9f2b3c4a5
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f3b2e91a6d4"
down_revision: Union[str, tuple[str, ...], None] = (
    "add_onboarding_completed_to_users",
    "c0e71c86214f",
    "e7d9f2b3c4a5",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("chunks_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_documents_id"), "rag_documents", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_documents_id"), table_name="rag_documents")
    op.drop_table("rag_documents")
