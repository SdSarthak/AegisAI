"""add role to user

Revision ID: 5c2d81ef246f
Revises: c3d9f1b2a4e6
Create Date: 2026-06-02 00:40:27.093070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c2d81ef246f'
down_revision: Union[str, None] = 'c3d9f1b2a4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
    )
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
    # ### end Alembic commands ###
