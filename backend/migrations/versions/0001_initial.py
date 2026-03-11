"""Initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255)),
        sa.Column("credits", sa.Integer(), server_default="350"),
        sa.Column("premium", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("premium_expires", sa.DateTime()),
        sa.Column("bio", sa.Text()),
        sa.Column("avatar_url", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime()),
        sa.Column("two_fa_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("email_notifications", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("marketing_emails", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("status", sa.String(length=50), server_default="active"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_username", sa.String(length=255)),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime()),
        sa.Column("scope", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "provider", name="unique_user_provider"),
    )

    op.create_table(
        "connected_platforms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_user_id", sa.String(length=255), nullable=False),
        sa.Column("platform_username", sa.String(length=255)),
        sa.Column("platform_display_name", sa.String(length=255)),
        sa.Column("profile_url", sa.String(length=500)),
        sa.Column("avatar_url", sa.String(length=500)),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime()),
        sa.Column("scope", sa.String(length=1000)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_sync", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "platform", name="unique_user_platform"),
    )

    op.create_table(
        "analytics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("posts_count", sa.Integer(), server_default="0"),
        sa.Column("views", sa.BigInteger(), server_default="0"),
        sa.Column("engagement", sa.Integer(), server_default="0"),
        sa.Column("followers", sa.Integer(), server_default="0"),
        sa.Column("new_followers", sa.Integer(), server_default="0"),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_user_platform_date", "analytics", ["user_id", "platform", "metric_date"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("user_agent", sa.String(length=500)),
        sa.Column("ip_address", sa.String(length=50)),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("token", name="uq_sessions_token"),
    )

    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("schedule_type", sa.String(length=20), nullable=False, server_default="now"),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("caption", sa.Text()),
        sa.Column("hashtags", sa.String(length=1000)),
        sa.Column("media_items", sa.JSON()),
        sa.Column("virality_score", sa.Integer()),
        sa.Column("external_post_id", sa.String(length=255)),
        sa.Column("publish_response", sa.JSON()),
        sa.Column("error_message", sa.String(length=500)),
        sa.Column("credits_spent", sa.Integer(), server_default="0"),
        sa.Column("credits_earned", sa.Integer(), server_default="0"),
        sa.Column("reward_granted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("published_at", sa.DateTime()),
    )
    op.create_index("ix_scheduled_posts_user_id", "scheduled_posts", ["user_id"])
    op.create_index("ix_scheduled_posts_platform", "scheduled_posts", ["platform"])
    op.create_index("ix_scheduled_posts_status", "scheduled_posts", ["status"])
    op.create_index("ix_scheduled_posts_scheduled_for", "scheduled_posts", ["scheduled_for"])
    op.create_index("ix_scheduled_posts_created_at", "scheduled_posts", ["created_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("reply", sa.Text()),
        sa.Column("replied_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "complaints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=50)),
        sa.Column("complaint_type", sa.String(length=100)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending"),
        sa.Column("assigned_to", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_table(
        "content_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("post_id", sa.String(length=255), nullable=False),
        sa.Column("reporter_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("report_type", sa.String(length=100)),
        sa.Column("status", sa.String(length=50), server_default="pending"),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("admin_id", sa.String(length=255), nullable=False),
        sa.Column("target", sa.String(length=255)),
        sa.Column("platform", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("activity_logs")
    op.drop_table("content_reports")
    op.drop_table("complaints")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("feedback")
    op.drop_index("ix_scheduled_posts_created_at", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_scheduled_for", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_status", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_platform", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_user_id", table_name="scheduled_posts")
    op.drop_table("scheduled_posts")
    op.drop_table("sessions")
    op.drop_index("idx_user_platform_date", table_name="analytics")
    op.drop_table("analytics")
    op.drop_table("connected_platforms")
    op.drop_table("oauth_accounts")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
