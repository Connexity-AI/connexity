"""add oauth dcr tables

Revision ID: v1w2x3y4z5a6
Revises: u1v2w3x4y5z6
Create Date: 2026-05-21

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "v1w2x3y4z5a6"
down_revision = "v2w3x4y5z6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_client",
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("redirect_uris", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("grant_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("token_endpoint_auth_method", sa.String(length=64), nullable=False),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_table(
        "oauth_authorization_code",
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("resource", sa.String(length=2048), nullable=False),
        sa.Column("code_challenge", sa.String(length=255), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_client.client_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index(
        op.f("ix_oauth_authorization_code_client_id"),
        "oauth_authorization_code",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth_authorization_code_user_id"),
        "oauth_authorization_code",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_oauth_authorization_code_user_id"),
        table_name="oauth_authorization_code",
    )
    op.drop_index(
        op.f("ix_oauth_authorization_code_client_id"),
        table_name="oauth_authorization_code",
    )
    op.drop_table("oauth_authorization_code")
    op.drop_table("oauth_client")
