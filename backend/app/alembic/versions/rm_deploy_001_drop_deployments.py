"""drop product-driven deploys: deployment table and environment deploy state

Revision ID: rm_deploy_001
Revises: rm_ai_assistant_001
Create Date: 2026-10-06

Connexity no longer deploys agents. The assistant deploys; the product has
read access to providers. Environments remain as the link between an agent and
its provider account. Downgrade restores the schema but not the data.
"""

import sqlalchemy as sa

from alembic import op

revision = "rm_deploy_001"
down_revision = "rm_ai_assistant_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("deployment")

    op.drop_constraint(
        "fk_environment_eval_gate_eval_config_id_eval_config",
        "environment",
        type_="foreignkey",
    )
    op.drop_index("ix_environment_eval_gate_eval_config_id", table_name="environment")
    op.drop_column("environment", "eval_gate_eval_config_id")
    op.drop_column("environment", "current_deployed_at")
    op.drop_column("environment", "current_version_name")
    op.drop_column("environment", "current_version_number")


def downgrade() -> None:
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
    op.add_column(
        "environment",
        sa.Column("eval_gate_eval_config_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_environment_eval_gate_eval_config_id",
        "environment",
        ["eval_gate_eval_config_id"],
    )
    op.create_foreign_key(
        "fk_environment_eval_gate_eval_config_id_eval_config",
        "environment",
        "eval_config",
        ["eval_gate_eval_config_id"],
        ["id"],
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
        sa.Column(
            "deployed_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["deployed_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["environment_id"], ["environment.id"]),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["company.id"],
            name="fk_deployment_company_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deployment_agent_id", "deployment", ["agent_id"])
    op.create_index("ix_deployment_company_id", "deployment", ["company_id"])
    op.create_index(
        "ix_deployment_deployed_by_user_id", "deployment", ["deployed_by_user_id"]
    )
    op.create_index(
        "ix_deployment_environment_deployed_at_desc",
        "deployment",
        ["environment_id", sa.text("deployed_at DESC")],
    )
    op.create_index("ix_deployment_environment_id", "deployment", ["environment_id"])
    op.create_index("ix_deployment_status", "deployment", ["status"])
