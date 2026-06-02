"""add ingested documents table

Revision ID: c8d4b0f6a2e1
Revises: c3d9f1b2a4e6
Create Date: 2026-05-31 21:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4b0f6a2e1"
down_revision: Union[str, None] = "c3d9f1b2a4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


source_type_enum = sa.Enum("UPLOADED", "PRE_LOADED", name="sourcetype")


def upgrade() -> None:
    op.create_table(
        "ingested_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column(
            "source_type",
            source_type_enum,
            server_default="UPLOADED",
            nullable=False,
        ),
        sa.Column("regulation_name", sa.String(length=200), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "file_size_bytes",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "chunk_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ingested_documents_id"),
        "ingested_documents",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingested_documents_file_hash"),
        "ingested_documents",
        ["file_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ingested_documents_file_hash"),
        table_name="ingested_documents",
    )
    op.drop_index(
        op.f("ix_ingested_documents_id"),
        table_name="ingested_documents",
    )
    op.drop_table("ingested_documents")
    source_type_enum.drop(op.get_bind(), checkfirst=True)
