"""Add user profile fields

Revision ID: 0002_user_profile_fields
Revises: 0001_initial
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_user_profile_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("username", sa.String(length=60), nullable=True))
    op.add_column("users", sa.Column("category", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("website", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("default_hashtags", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("default_cta", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("users", "default_cta")
    op.drop_column("users", "default_hashtags")
    op.drop_column("users", "website")
    op.drop_column("users", "category")
    op.drop_column("users", "username")
