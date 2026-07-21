"""hash rag_queries and rag_feedback plaintext columns

Revision ID: 4d8e9f0a1b2c
Revises: 7f3b2e91a6d4
Create Date: 2026-06-19 00:00:00.000000
"""
revision = "4d8e9f0a1b2c"
down_revision = "7f3b2e91a6d4"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # --- rag_queries ---
    op.add_column("rag_queries", sa.Column("question_hash", sa.String(64), nullable=True))
    op.add_column("rag_queries", sa.Column("question_length", sa.Integer(), nullable=True))
    op.add_column("rag_queries", sa.Column("answer_hash", sa.String(64), nullable=True))
    op.add_column("rag_queries", sa.Column("answer_length", sa.Integer(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE rag_queries
            SET question_hash = encode(sha256(question::bytea), 'hex'),
                question_length = length(question)
        """)
    )

    op.alter_column("rag_queries", "question_hash", nullable=False)
    op.drop_column("rag_queries", "question")
    op.drop_column("rag_queries", "answer_summary")

    # --- rag_feedback ---
    op.add_column("rag_feedback", sa.Column("question_hash", sa.String(64), nullable=True))
    op.add_column("rag_feedback", sa.Column("answer_hash", sa.String(64), nullable=True))

    conn.execute(
        sa.text("""
            UPDATE rag_feedback
            SET question_hash = encode(sha256(question::bytea), 'hex'),
                answer_hash = encode(sha256(answer::bytea), 'hex')
            WHERE question IS NOT NULL
        """)
    )

    op.drop_column("rag_feedback", "question")
    op.drop_column("rag_feedback", "answer")


def downgrade():
    # --- rag_feedback ---
    op.add_column("rag_feedback", sa.Column("answer", sa.String(4000), nullable=True))
    op.add_column("rag_feedback", sa.Column("question", sa.String(2000), nullable=True))
    op.drop_column("rag_feedback", "answer_hash")
    op.drop_column("rag_feedback", "question_hash")

    # --- rag_queries ---
    op.add_column("rag_queries", sa.Column("answer_summary", sa.String(200), nullable=True))
    op.add_column("rag_queries", sa.Column("question", sa.Text(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE rag_queries
            SET question = ''
        """)
    )
    op.alter_column("rag_queries", "question", nullable=False)

    op.drop_column("rag_queries", "answer_length")
    op.drop_column("rag_queries", "answer_hash")
    op.drop_column("rag_queries", "question_length")
    op.drop_column("rag_queries", "question_hash")
