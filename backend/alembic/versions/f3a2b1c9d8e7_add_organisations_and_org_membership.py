"""Add organisations, organisation_members tables and org_id columns.

Revision ID: f3a2b1c9d8e7
Revises: eb8060353ac6
Create Date: 2026-05-30

Adds multi-tenancy support (GitHub issue #85):
  - organisations table
  - organisation_members join table
  - org_id nullable FK on users, ai_systems, documents
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a2b1c9d8e7"
down_revision = "eb8060353ac6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Create organisations table
    # -----------------------------------------------------------------------
    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organisation_slug"),
    )
    op.create_index("ix_organisations_id", "organisations", ["id"], unique=False)
    op.create_index("ix_organisations_slug", "organisations", ["slug"], unique=True)

    # -----------------------------------------------------------------------
    # 2. Create organisation_members join table
    # -----------------------------------------------------------------------
    op.create_table(
        "organisation_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "member", name="orgrole"),
            nullable=False,
        ),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_organisation_members_id", "organisation_members", ["id"], unique=False)

    # -----------------------------------------------------------------------
    # 3. Add org_id to users (nullable — existing users are unaffected)
    # -----------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("org_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_org_id_organisations",
        "users",
        "organisations",
        ["org_id"],
        ["id"],
    )
    op.create_index("ix_users_org_id", "users", ["org_id"], unique=False)

    # -----------------------------------------------------------------------
    # 4. Add org_id to ai_systems (nullable — existing rows are unaffected)
    # -----------------------------------------------------------------------
    op.add_column(
        "ai_systems",
        sa.Column("org_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_systems_org_id_organisations",
        "ai_systems",
        "organisations",
        ["org_id"],
        ["id"],
    )
    op.create_index("ix_ai_systems_org_id", "ai_systems", ["org_id"], unique=False)

    # Unique constraint: within one org, system names must be unique
    op.create_unique_constraint(
        "uq_ai_system_org_name",
        "ai_systems",
        ["org_id", "name"],
    )

    # -----------------------------------------------------------------------
    # 5. Add org_id to documents (nullable — existing rows are unaffected)
    # -----------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column("org_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_org_id_organisations",
        "documents",
        "organisations",
        ["org_id"],
        ["id"],
    )
    op.create_index("ix_documents_org_id", "documents", ["org_id"], unique=False)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Reverse all changes in opposite order
    # -----------------------------------------------------------------------
    op.drop_index("ix_documents_org_id", table_name="documents")
    op.drop_constraint("fk_documents_org_id_organisations", "documents", type_="foreignkey")
    op.drop_column("documents", "org_id")

    op.drop_constraint("uq_ai_system_org_name", "ai_systems", type_="unique")
    op.drop_index("ix_ai_systems_org_id", table_name="ai_systems")
    op.drop_constraint("fk_ai_systems_org_id_organisations", "ai_systems", type_="foreignkey")
    op.drop_column("ai_systems", "org_id")

    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_constraint("fk_users_org_id_organisations", "users", type_="foreignkey")
    op.drop_column("users", "org_id")

    op.drop_index("ix_organisation_members_id", table_name="organisation_members")
    op.drop_table("organisation_members")

    op.drop_index("ix_organisations_slug", table_name="organisations")
    op.drop_index("ix_organisations_id", table_name="organisations")
    op.drop_table("organisations")

    # Drop the enum type (PostgreSQL only — SQLite handles enums as VARCHAR)
    try:
        orgrole_enum = sa.Enum(name="orgrole")
        orgrole_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
