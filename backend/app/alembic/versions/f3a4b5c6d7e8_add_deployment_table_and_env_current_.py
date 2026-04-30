"""add deployment table and environment current version columns

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-04-27 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "environment",
        sa.Column("current_version_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "environment",
        sa.Column("current_version_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "environment",
        sa.Column("current_deployed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "deployment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("agent_version", sa.Integer(), nullable=False),
        sa.Column("retell_version_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("deployed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("deployed_by_name", sa.String(length=255), nullable=True),
        sa.Column(
            "deployed_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["environment_id"], ["environment.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["deployed_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deployment_environment_id"),
        "deployment",
        ["environment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deployment_agent_id"), "deployment", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_deployment_status"), "deployment", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_deployment_deployed_by_user_id"),
        "deployment",
        ["deployed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_deployment_environment_deployed_at_desc",
        "deployment",
        ["environment_id", sa.text("deployed_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_deployment_environment_deployed_at_desc", table_name="deployment"
    )
    op.drop_index(op.f("ix_deployment_deployed_by_user_id"), table_name="deployment")
    op.drop_index(op.f("ix_deployment_status"), table_name="deployment")
    op.drop_index(op.f("ix_deployment_agent_id"), table_name="deployment")
    op.drop_index(op.f("ix_deployment_environment_id"), table_name="deployment")
    op.drop_table("deployment")

    op.drop_column("environment", "current_deployed_at")
    op.drop_column("environment", "current_version_name")
    op.drop_column("environment", "current_version_number")
