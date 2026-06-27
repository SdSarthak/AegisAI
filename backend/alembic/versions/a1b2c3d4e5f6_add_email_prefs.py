"""add email prefs

Revision ID: a1b2c3d4e5f6
Revises: 0d84589831eb
Create Date: 2026-06-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '0d84589831eb'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('email_notifications_enabled', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('email_notification_frequency', sa.String(length=50), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'email_notification_frequency')
    op.drop_column('users', 'email_notifications_enabled')