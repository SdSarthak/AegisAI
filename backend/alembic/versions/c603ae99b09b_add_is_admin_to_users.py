"""add_is_admin_to_users

Revision ID: c603ae99b09b
Revises: eb8060353ac6
Create Date: 2026-07-05 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c603ae99b09b"
down_revision: Union[str, None] = "eb8060353ac6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
