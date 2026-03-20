"""add eval domain core entities

Revision ID: a1b2c3d4e5f6
Revises: 52186b4ceb64
Create Date: 2026-03-19 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "52186b4ceb64"
branch_labels = None
depends_on = None


def upgrade():
    # Enums
    difficulty_enum = postgresql.ENUM(
        "normal", "hard", name="difficulty", create_type=False
    )
    scenariostatus_enum = postgresql.ENUM(
        "draft", "active", "archived", name="scenariostatus", create_type=False
    )
    simulationmode_enum = postgresql.ENUM(
        "scripted", "llm_driven", name="simulationmode", create_type=False
    )
    runstatus_enum = postgresql.ENUM(
        "pending", "running", "completed", "failed", "cancelled",
        name="runstatus", create_type=False,
    )
    errorcategory_enum = postgresql.ENUM(
        "none", "off_topic", "hallucination", "refusal", "tool_misuse",
        "safety_violation", "prompt_violation", "incomplete",
        "latency_timeout", "agent_error", "other",
        name="errorcategory", create_type=False,
    )

    # Create enum types in PostgreSQL
    difficulty_enum.create(op.get_bind(), checkfirst=True)
    scenariostatus_enum.create(op.get_bind(), checkfirst=True)
    simulationmode_enum.create(op.get_bind(), checkfirst=True)
    runstatus_enum.create(op.get_bind(), checkfirst=True)
    errorcategory_enum.create(op.get_bind(), checkfirst=True)

    # ── agents ─────────────────────────────────────────────────────
    op.create_table(
        "agent",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("endpoint_url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── scenarios ──────────────────────────────────────────────────
    op.create_table(
        "scenario",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("difficulty", difficulty_enum, nullable=False, server_default="normal"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", scenariostatus_enum, nullable=False, server_default="active"),
        sa.Column("simulation_mode", simulationmode_enum, nullable=False, server_default="llm_driven"),
        sa.Column("scripted_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_persona", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("user_goal", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("initial_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("max_turns", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("expected_outcomes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("evaluation_criteria_override", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_difficulty", "scenario", ["difficulty"])
    op.create_index("ix_scenario_status", "scenario", ["status"])
    op.create_index("ix_scenario_tags_gin", "scenario", ["tags"], postgresql_using="gin")

    # ── scenario_sets ──────────────────────────────────────────────
    op.create_table(
        "scenario_set",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_set_name", "scenario_set", ["name"])

    # ── scenario_set_members (join table) ──────────────────────────
    op.create_table(
        "scenario_set_member",
        sa.Column("scenario_set_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["scenario_set_id"], ["scenario_set.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario.id"]),
        sa.PrimaryKeyConstraint("scenario_set_id", "scenario_id"),
    )
    op.create_index("ix_scenario_set_member_set_id", "scenario_set_member", ["scenario_set_id"])

    # ── runs ───────────────────────────────────────────────────────
    op.create_table(
        "run",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("agent_endpoint_url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
        sa.Column("agent_system_prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("agent_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prompt_version", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("prompt_snapshot", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tools_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tools_snapshot_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("scenario_set_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_set_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", runstatus_enum, nullable=False, server_default="pending"),
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("aggregate_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["scenario_set_id"], ["scenario_set.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_agent_id", "run", ["agent_id"])
    op.create_index("ix_run_status", "run", ["status"])
    op.create_index("ix_run_is_baseline", "run", ["is_baseline"])
    op.create_index("ix_run_created_at", "run", ["created_at"])
    op.create_index("ix_run_scenario_set_id", "run", ["scenario_set_id"])

    # ── scenario_results ───────────────────────────────────────────
    op.create_table(
        "scenario_result",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("transcript", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("turn_count", sa.Integer(), nullable=True),
        sa.Column("verdict", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("agent_latency_p50_ms", sa.Integer(), nullable=True),
        sa.Column("agent_latency_p95_ms", sa.Integer(), nullable=True),
        sa.Column("agent_latency_max_ms", sa.Integer(), nullable=True),
        sa.Column("agent_token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("platform_token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("error_category", errorcategory_enum, nullable=False, server_default="none"),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_result_run_id", "scenario_result", ["run_id"])
    op.create_index("ix_scenario_result_scenario_id", "scenario_result", ["scenario_id"])
    op.create_index("ix_scenario_result_passed", "scenario_result", ["passed"])
    op.create_index("ix_scenario_result_error_category", "scenario_result", ["error_category"])


def downgrade():
    # Drop tables in reverse dependency order
    op.drop_table("scenario_result")
    op.drop_table("run")
    op.drop_table("scenario_set_member")
    op.drop_table("scenario_set")
    op.drop_table("scenario")
    op.drop_table("agent")

    # Drop enum types
    sa.Enum(name="errorcategory").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="runstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="simulationmode").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="scenariostatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="difficulty").drop(op.get_bind(), checkfirst=True)
