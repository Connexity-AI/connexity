"""The old eval stack goes: Connexity's own agent versions, environments, custom
metrics, and the columns only the old runner, its routes and the agent editor wrote
(`plans/2026-11-20-remove-old-eval-stack.md`). Scenarios, sets, runs and simulated
calls keep their rows. The downgrade brings the tables and columns back empty.

Revision ID: 0040_remove_old_eval_stack
Revises: 0039_runs_have_a_version
Create Date: 2026-11-20 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0040_remove_old_eval_stack"
down_revision = "0039_runs_have_a_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_environment_agent_id", table_name="environment")
    op.drop_index("ix_environment_company_id", table_name="environment")
    op.drop_table("environment")
    op.drop_index("ix_custom_metric_company_id", table_name="custom_metric")
    op.drop_index("ix_custom_metric_created_by", table_name="custom_metric")
    op.drop_index("ix_custom_metric_deleted_at", table_name="custom_metric")
    op.drop_index(
        "uq_custom_metric_company_name_active",
        table_name="custom_metric",
        postgresql_where="(deleted_at IS NULL)",
    )
    op.drop_table("custom_metric")
    op.drop_column("agent", "tools")
    op.drop_column("agent", "prompt_type")
    op.drop_column("agent", "agent_provider")
    op.drop_column("agent", "has_draft")
    op.drop_column("agent", "agent_model")
    op.drop_column("agent", "agent_temperature")
    op.drop_column("agent", "endpoint_url")
    op.drop_column("agent", "system_prompt")
    op.drop_column("eval_config_member", "repetitions")
    op.drop_index("ix_run_agent_version", table_name="run")
    op.drop_index("ix_run_agent_version_id", table_name="run")
    op.drop_index("ix_run_is_baseline", table_name="run")
    op.drop_constraint("run_agent_version_id_fkey", "run", type_="foreignkey")
    op.drop_column("run", "agent_tools")
    op.drop_column("run", "agent_endpoint_url")
    op.drop_column("run", "aggregate_metrics")
    op.drop_column("run", "eval_config_version")
    op.drop_column("run", "agent_provider")
    op.drop_column("run", "agent_version_id")
    op.drop_column("run", "agent_system_prompt")
    op.drop_column("run", "agent_version")
    op.drop_column("run", "agent_model")
    op.drop_column("run", "is_baseline")
    op.drop_column("run", "name")
    op.drop_index("ix_test_case_difficulty", table_name="test_case")
    op.drop_index(
        "ix_test_case_tags_gin", table_name="test_case", postgresql_using="gin"
    )
    op.drop_column("test_case", "difficulty")
    op.drop_column("test_case", "evaluation_criteria_override")
    op.drop_column("test_case", "tags")
    op.drop_index("ix_test_case_result_passed", table_name="test_case_result")
    op.drop_column("test_case_result", "verdict")
    op.drop_column("test_case_result", "agent_latency_max_ms")
    op.drop_column("test_case_result", "passed")
    op.drop_column("test_case_result", "agent_latency_per_turn_ms")
    op.drop_column("test_case_result", "total_latency_ms")
    op.drop_column("test_case_result", "agent_latency_p95_ms")
    op.drop_column("test_case_result", "agent_latency_p50_ms")
    # Last: `run.agent_version_id` pointed at it.
    op.drop_index("ix_agent_version_agent_id", table_name="agent_version")
    op.drop_index(
        "ix_agent_version_agent_id_created_at_desc", table_name="agent_version"
    )
    op.drop_index("ix_agent_version_company_id", table_name="agent_version")
    op.drop_index("ix_agent_version_created_by", table_name="agent_version")
    op.drop_index(
        "ix_agent_version_one_active_published_per_agent",
        table_name="agent_version",
        postgresql_where="(is_active AND (version IS NOT NULL))",
    )
    op.drop_index(
        "ix_agent_version_one_draft_per_agent",
        table_name="agent_version",
        postgresql_where="((status)::text = 'draft'::text)",
    )
    op.drop_table("agent_version")


def downgrade() -> None:
    # First: `run.agent_version_id` points at it.
    op.create_table(
        "agent_version",
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("agent_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("version", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("status", sa.VARCHAR(length=32), autoincrement=False, nullable=False),
        sa.Column("mode", sa.VARCHAR(length=32), autoincrement=False, nullable=False),
        sa.Column(
            "endpoint_url", sa.VARCHAR(length=2048), autoincrement=False, nullable=True
        ),
        sa.Column("system_prompt", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "tools",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "agent_model", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
        sa.Column(
            "agent_provider", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
        sa.Column(
            "agent_temperature",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column("version_name", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "version_description", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
        sa.Column("created_by", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "NOT is_active OR version IS NOT NULL", name="ck_agent_version_active_rules"
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.id"],
            name="agent_version_agent_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["company.id"], name="agent_version_company_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], name="agent_version_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="agent_version_pkey"),
        sa.UniqueConstraint(
            "agent_id", "version", name="uq_agent_version_agent_version"
        ),
    )
    op.create_index(
        "ix_agent_version_one_draft_per_agent",
        "agent_version",
        ["agent_id"],
        unique=True,
        postgresql_where="((status)::text = 'draft'::text)",
    )
    op.create_index(
        "ix_agent_version_one_active_published_per_agent",
        "agent_version",
        ["agent_id"],
        unique=True,
        postgresql_where="(is_active AND (version IS NOT NULL))",
    )
    op.create_index(
        "ix_agent_version_created_by", "agent_version", ["created_by"], unique=False
    )
    op.create_index(
        "ix_agent_version_company_id", "agent_version", ["company_id"], unique=False
    )
    op.create_index(
        "ix_agent_version_agent_id_created_at_desc",
        "agent_version",
        ["agent_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_agent_version_agent_id", "agent_version", ["agent_id"], unique=False
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "agent_latency_p50_ms", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "agent_latency_p95_ms", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "test_case_result",
        sa.Column("total_latency_ms", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "agent_latency_per_turn_ms",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "test_case_result",
        sa.Column("passed", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "agent_latency_max_ms", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "verdict",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_index(
        "ix_test_case_result_passed", "test_case_result", ["passed"], unique=False
    )
    op.add_column(
        "test_case",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.TEXT()),
            server_default=sa.text("'{}'::text[]"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "test_case",
        sa.Column(
            "evaluation_criteria_override",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "test_case",
        sa.Column(
            "difficulty",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=False,
            server_default="normal",
        ),
    )
    op.create_index(
        "ix_test_case_tags_gin",
        "test_case",
        ["tags"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_test_case_difficulty", "test_case", ["difficulty"], unique=False
    )
    op.add_column(
        "run",
        sa.Column("name", sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    )
    op.add_column(
        "run",
        sa.Column(
            "is_baseline",
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_model", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "run",
        sa.Column("agent_version", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_system_prompt", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "run",
        sa.Column("agent_version_id", sa.UUID(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_provider", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "eval_config_version",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "aggregate_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_endpoint_url",
            sa.VARCHAR(length=2048),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_tools",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "run_agent_version_id_fkey",
        "run",
        "agent_version",
        ["agent_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_run_is_baseline", "run", ["is_baseline"], unique=False)
    op.create_index(
        "ix_run_agent_version_id", "run", ["agent_version_id"], unique=False
    )
    op.add_column(
        "eval_config_member",
        sa.Column(
            "repetitions",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "agent",
        sa.Column("system_prompt", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "agent",
        sa.Column(
            "endpoint_url", sa.VARCHAR(length=2048), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "agent_temperature",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "agent_model", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "has_draft",
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "agent_provider", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "prompt_type",
            sa.VARCHAR(length=32),
            autoincrement=False,
            nullable=False,
            server_default="single_prompt",
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "tools",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_table(
        "custom_metric",
        sa.Column("name", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column(
            "display_name", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column("description", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("tier", sa.VARCHAR(length=32), autoincrement=False, nullable=False),
        sa.Column(
            "default_weight",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "score_type", sa.VARCHAR(length=32), autoincrement=False, nullable=False
        ),
        sa.Column("rubric", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "include_in_defaults", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
        sa.Column("is_predefined", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column("is_draft", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column("created_by", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "deleted_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["company.id"], name="custom_metric_company_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], name="custom_metric_created_by_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="custom_metric_pkey"),
    )
    op.create_index(
        "uq_custom_metric_company_name_active",
        "custom_metric",
        ["company_id", "name"],
        unique=True,
        postgresql_where="(deleted_at IS NULL)",
    )
    op.create_index(
        "ix_custom_metric_deleted_at", "custom_metric", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_custom_metric_created_by", "custom_metric", ["created_by"], unique=False
    )
    op.create_index(
        "ix_custom_metric_company_id", "custom_metric", ["company_id"], unique=False
    )
    op.create_table(
        "environment",
        sa.Column("name", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column(
            "platform", sa.VARCHAR(length=32), autoincrement=False, nullable=False
        ),
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("agent_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "endpoint_url", sa.VARCHAR(length=2048), autoincrement=False, nullable=True
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agent.id"], name="environment_agent_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["company.id"], name="environment_company_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="environment_pkey"),
    )
    op.create_index(
        "ix_environment_company_id", "environment", ["company_id"], unique=False
    )
    op.create_index(
        "ix_environment_agent_id", "environment", ["agent_id"], unique=False
    )
    op.create_index("ix_run_agent_version", "run", ["agent_version"], unique=False)
