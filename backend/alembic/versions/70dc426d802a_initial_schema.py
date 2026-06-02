"""initial_schema

Revision ID: 70dc426d802a
Revises: 
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "70dc426d802a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column(
            "subscription_tier",
            sa.Enum("free", "starter", "growth", "scale", name="subscriptiontier"),
            nullable=True,
        ),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # --- ai_systems ---
    op.create_table(
        "ai_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("use_case", sa.String(length=255), nullable=True),
        sa.Column("sector", sa.String(length=255), nullable=True),
        sa.Column(
            "risk_level",
            sa.Enum("unacceptable", "high", "limited", "minimal", name="risklevel"),
            nullable=True,
        ),
        sa.Column(
            "compliance_status",
            sa.Enum(
                "not_started",
                "in_progress",
                "under_review",
                "compliant",
                "non_compliant",
                name="compliancestatus",
            ),
            nullable=True,
        ),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("questionnaire_responses", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_systems_id"), "ai_systems", ["id"], unique=False)

    # --- risk_assessments ---
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ai_system_id", sa.Integer(), nullable=False),
        sa.Column("assessment_type", sa.String(length=100), nullable=True),
        sa.Column(
            "risk_level",
            sa.Enum("unacceptable", "high", "limited", "minimal", name="risklevel"),
            nullable=True,
        ),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("data_governance_score", sa.Integer(), nullable=True),
        sa.Column("transparency_score", sa.Integer(), nullable=True),
        sa.Column("human_oversight_score", sa.Integer(), nullable=True),
        sa.Column("robustness_score", sa.Integer(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ai_system_id"], ["ai_systems.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_assessments_id"), "risk_assessments", ["id"], unique=False
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("ai_system_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "technical_documentation",
                "risk_assessment",
                "conformity_declaration",
                "data_governance",
                "transparency_notice",
                "human_oversight_plan",
                "incident_report",
                name="documenttype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "generated", "reviewed", "approved", "archived",
                name="documentstatus",
            ),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ai_system_id"], ["ai_systems.id"],),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)

    # --- document_versions ---
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_versions_id"), "document_versions", ["id"], unique=False
    )

    # --- guard_scan_logs (base columns only; extras added by eb8060353ac6) ---
    op.create_table(
        "guard_scan_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("matched_patterns", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_guard_scan_logs_id"), "guard_scan_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_guard_scan_logs_user_id"),
        "guard_scan_logs",
        ["user_id"],
        unique=False,
    )

    # --- rag_feedback ---
    op.create_table(
        "rag_feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=2000), nullable=True),
        sa.Column("answer", sa.String(length=4000), nullable=True),
        sa.Column("thumbs_up", sa.Integer(), nullable=True),
        sa.Column("thumbs_down", sa.Integer(), nullable=True),
        sa.Column("source_chunks", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- rag_queries ---
    op.create_table(
        "rag_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer_summary", sa.String(length=200), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_queries_id"), "rag_queries", ["id"], unique=False)

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_id"), "notifications", ["id"], unique=False
    )

    # --- compliance_snapshots ---
    op.create_table(
        "compliance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ai_system_id", sa.Integer(), nullable=False),
        sa.Column("compliance_score", sa.Integer(), nullable=False),
        sa.Column("compliance_status", sa.String(length=50), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("snapshotted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ai_system_id"], ["ai_systems.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_compliance_snapshots_id"),
        "compliance_snapshots",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("compliance_snapshots")
    op.drop_table("notifications")
    op.drop_table("rag_queries")
    op.drop_table("rag_feedback")
    op.drop_table("guard_scan_logs")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("risk_assessments")
    op.drop_table("ai_systems")
    op.drop_table("users")

    sa.Enum(name="subscriptiontier").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="risklevel").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="compliancestatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="documenttype").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="documentstatus").drop(op.get_bind(), checkfirst=False)
