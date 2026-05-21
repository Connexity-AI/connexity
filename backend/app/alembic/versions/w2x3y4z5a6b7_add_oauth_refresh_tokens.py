"""add oauth refresh tokens

Revision ID: w2x3y4z5a6b7
Revises: v1w2x3y4z5a6
Create Date: 2026-05-21

"""

from alembic import op
import sqlalchemy as sa

revision = "w2x3y4z5a6b7"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_refresh_token",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("resource", sa.String(length=2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_client.client_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_oauth_refresh_token_client_id"),
        "oauth_refresh_token",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth_refresh_token_user_id"),
        "oauth_refresh_token",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_refresh_token_user_id"), table_name="oauth_refresh_token")
    op.drop_index(op.f("ix_oauth_refresh_token_client_id"), table_name="oauth_refresh_token")
    op.drop_table("oauth_refresh_token")
