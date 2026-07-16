"""add_rag_queries_table

Revision ID: c0e71c86214f
Revises: c3d9f1b2a4e6
Create Date: 2026-05-24 19:51:58.566264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c0e71c86214f'
down_revision: Union[str, Sequence[str], None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
<<<<<<< HEAD
    op.create_table(
        'rag_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer_summary', sa.Text(), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
=======
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'rag_queries' not in inspector.get_table_names():
        op.create_table(
            'rag_queries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('question', sa.Text(), nullable=False),
            sa.Column('answer_summary', sa.Text(), nullable=True),
            sa.Column('source_count', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
>>>>>>> 0e31294 (fix: make alembic table migrations idempotent)


def downgrade() -> None:
    op.drop_table('rag_queries')