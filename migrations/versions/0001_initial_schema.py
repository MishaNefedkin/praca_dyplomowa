"""Initial CRM analytics schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("session_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_clients_email"), "clients", ["email"], unique=False)
    op.create_index(op.f("ix_clients_id"), "clients", ["id"], unique=False)
    op.create_index(op.f("ix_clients_session_id"), "clients", ["session_id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("login", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_login"), "users", ["login"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("page_url", sa.String(length=500), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column("time_on_page", sa.Integer(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_logs_client_id"), "activity_logs", ["client_id"], unique=False)
    op.create_index(op.f("ix_activity_logs_event_type"), "activity_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_activity_logs_id"), "activity_logs", ["id"], unique=False)
    op.create_index(op.f("ix_activity_logs_logged_at"), "activity_logs", ["logged_at"], unique=False)
    op.create_index(op.f("ix_activity_logs_session_id"), "activity_logs", ["session_id"], unique=False)

    op.create_table(
        "consents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consents_client_id"), "consents", ["client_id"], unique=False)
    op.create_index(op.f("ix_consents_id"), "consents", ["id"], unique=False)

    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inquiries_client_id"), "inquiries", ["client_id"], unique=False)
    op.create_index(op.f("ix_inquiries_id"), "inquiries", ["id"], unique=False)
    op.create_index(op.f("ix_inquiries_status"), "inquiries", ["status"], unique=False)

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inquiry_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["inquiry_id"], ["inquiries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_offers_id"), "offers", ["id"], unique=False)
    op.create_index(op.f("ix_offers_inquiry_id"), "offers", ["inquiry_id"], unique=False)
    op.create_index(op.f("ix_offers_status"), "offers", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_offers_status"), table_name="offers")
    op.drop_index(op.f("ix_offers_inquiry_id"), table_name="offers")
    op.drop_index(op.f("ix_offers_id"), table_name="offers")
    op.drop_table("offers")

    op.drop_index(op.f("ix_inquiries_status"), table_name="inquiries")
    op.drop_index(op.f("ix_inquiries_id"), table_name="inquiries")
    op.drop_index(op.f("ix_inquiries_client_id"), table_name="inquiries")
    op.drop_table("inquiries")

    op.drop_index(op.f("ix_consents_id"), table_name="consents")
    op.drop_index(op.f("ix_consents_client_id"), table_name="consents")
    op.drop_table("consents")

    op.drop_index(op.f("ix_activity_logs_session_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_logged_at"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_event_type"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_client_id"), table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_login"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_clients_session_id"), table_name="clients")
    op.drop_index(op.f("ix_clients_id"), table_name="clients")
    op.drop_index(op.f("ix_clients_email"), table_name="clients")
    op.drop_table("clients")
