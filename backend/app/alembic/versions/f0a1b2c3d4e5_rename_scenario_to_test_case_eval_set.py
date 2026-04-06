"""rename scenario tables/columns to test_case and eval_set

Revision ID: f0a1b2c3d4e5
Revises: e4f5a6b7c8d9
Create Date: 2026-04-06 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "f0a1b2c3d4e5"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Drop foreign keys (dependency order) ---
    op.drop_constraint("fk_scenario_agent_id_agent", "scenario", type_="foreignkey")
    op.drop_constraint("run_scenario_set_id_fkey", "run", type_="foreignkey")
    op.drop_constraint(
        "scenario_set_member_scenario_id_fkey", "scenario_set_member", type_="foreignkey"
    )
    op.drop_constraint(
        "scenario_set_member_scenario_set_id_fkey",
        "scenario_set_member",
        type_="foreignkey",
    )
    op.drop_constraint(
        "scenario_result_scenario_id_fkey", "scenario_result", type_="foreignkey"
    )

    # Join table PK must be dropped before column renames
    op.drop_constraint("scenario_set_member_pkey", "scenario_set_member", type_="primary")

    op.drop_constraint(
        "ck_scenario_set_member_repetitions_ge_1", "scenario_set_member", type_="check"
    )
    op.drop_constraint(
        "ck_scenario_set_set_repetitions_ge_1", "scenario_set", type_="check"
    )

    # --- Column renames (before table renames) ---
    op.alter_column(
        "scenario_set_member",
        "scenario_set_id",
        new_column_name="eval_set_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "scenario_set_member",
        "scenario_id",
        new_column_name="test_case_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )

    op.alter_column(
        "run",
        "scenario_set_id",
        new_column_name="eval_set_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "run",
        "scenario_set_version",
        new_column_name="eval_set_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.alter_column(
        "scenario_result",
        "scenario_id",
        new_column_name="test_case_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )

    # --- Table renames ---
    op.rename_table("scenario", "test_case")
    op.rename_table("scenario_set", "eval_set")
    op.rename_table("scenario_set_member", "eval_set_member")
    op.rename_table("scenario_result", "test_case_result")

    op.execute(sa.text("ALTER TYPE scenariostatus RENAME TO testcasestatus"))

    # --- Indexes on test_case (formerly scenario) ---
    op.execute(sa.text("ALTER INDEX ix_scenario_difficulty RENAME TO ix_test_case_difficulty"))
    op.execute(sa.text("ALTER INDEX ix_scenario_status RENAME TO ix_test_case_status"))
    op.execute(sa.text("ALTER INDEX ix_scenario_tags_gin RENAME TO ix_test_case_tags_gin"))
    op.execute(sa.text("ALTER INDEX ix_scenario_agent_id RENAME TO ix_test_case_agent_id"))

    # --- eval_set ---
    op.execute(sa.text("ALTER INDEX ix_scenario_set_name RENAME TO ix_eval_set_name"))

    # --- eval_set_member ---
    op.execute(
        sa.text(
            "ALTER INDEX ix_scenario_set_member_scenario_set_id "
            "RENAME TO ix_eval_set_member_eval_set_id"
        )
    )

    # --- test_case_result ---
    op.execute(
        sa.text(
            "ALTER INDEX ix_scenario_result_passed RENAME TO ix_test_case_result_passed"
        )
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_scenario_result_run_id RENAME TO ix_test_case_result_run_id"
        )
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_scenario_result_scenario_id "
            "RENAME TO ix_test_case_result_test_case_id"
        )
    )

    # --- run index on eval_set fk ---
    op.execute(
        sa.text("ALTER INDEX ix_run_scenario_set_id RENAME TO ix_run_eval_set_id")
    )

    # --- Primary key on join table ---
    op.create_primary_key("eval_set_member_pkey", "eval_set_member", ["eval_set_id", "test_case_id"])

    op.create_check_constraint(
        "ck_eval_set_member_repetitions_ge_1",
        "eval_set_member",
        "repetitions >= 1",
    )
    op.create_check_constraint(
        "ck_eval_set_set_repetitions_ge_1",
        "eval_set",
        "set_repetitions >= 1",
    )

    # --- Recreate foreign keys ---
    op.create_foreign_key(
        "fk_test_case_agent_id_agent",
        "test_case",
        "agent",
        ["agent_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_run_eval_set_id_eval_set",
        "run",
        "eval_set",
        ["eval_set_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_eval_set_member_test_case_id_test_case",
        "eval_set_member",
        "test_case",
        ["test_case_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_eval_set_member_eval_set_id_eval_set",
        "eval_set_member",
        "eval_set",
        ["eval_set_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_test_case_result_test_case_id_test_case",
        "test_case_result",
        "test_case",
        ["test_case_id"],
        ["id"],
    )

    # --- JSONB key migrations for API field renames ---
    op.execute(
        sa.text("""
            UPDATE run
            SET config = (
                CASE
                    WHEN config ? 'timeout_per_scenario_ms' THEN
                        (config - 'timeout_per_scenario_ms')
                        || jsonb_build_object(
                            'timeout_per_test_case_ms',
                            config->'timeout_per_scenario_ms'
                        )
                    ELSE config
                END
            )
            WHERE config IS NOT NULL AND config ? 'timeout_per_scenario_ms'
        """)
    )
    op.execute(
        sa.text("""
            UPDATE run
            SET aggregate_metrics = (
                CASE
                    WHEN aggregate_metrics ? 'total_scenarios' THEN
                        (aggregate_metrics - 'total_scenarios')
                        || jsonb_build_object(
                            'unique_test_case_count',
                            aggregate_metrics->'total_scenarios'
                        )
                    ELSE aggregate_metrics
                END
            )
            WHERE aggregate_metrics IS NOT NULL
              AND aggregate_metrics ? 'total_scenarios'
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE run
            SET aggregate_metrics = (
                CASE
                    WHEN aggregate_metrics ? 'unique_test_case_count' THEN
                        (aggregate_metrics - 'unique_test_case_count')
                        || jsonb_build_object(
                            'total_scenarios',
                            aggregate_metrics->'unique_test_case_count'
                        )
                    ELSE aggregate_metrics
                END
            )
            WHERE aggregate_metrics IS NOT NULL
              AND aggregate_metrics ? 'unique_test_case_count'
        """)
    )
    op.execute(
        sa.text("""
            UPDATE run
            SET config = (
                CASE
                    WHEN config ? 'timeout_per_test_case_ms' THEN
                        (config - 'timeout_per_test_case_ms')
                        || jsonb_build_object(
                            'timeout_per_scenario_ms',
                            config->'timeout_per_test_case_ms'
                        )
                    ELSE config
                END
            )
            WHERE config IS NOT NULL AND config ? 'timeout_per_test_case_ms'
        """)
    )

    op.drop_constraint(
        "fk_test_case_result_test_case_id_test_case",
        "test_case_result",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_eval_set_member_eval_set_id_eval_set", "eval_set_member", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_eval_set_member_test_case_id_test_case", "eval_set_member", type_="foreignkey"
    )
    op.drop_constraint("fk_run_eval_set_id_eval_set", "run", type_="foreignkey")
    op.drop_constraint("fk_test_case_agent_id_agent", "test_case", type_="foreignkey")

    op.drop_constraint("ck_eval_set_set_repetitions_ge_1", "eval_set", type_="check")
    op.drop_constraint(
        "ck_eval_set_member_repetitions_ge_1", "eval_set_member", type_="check"
    )
    op.drop_constraint("eval_set_member_pkey", "eval_set_member", type_="primary")

    op.execute(
        sa.text("ALTER INDEX ix_run_eval_set_id RENAME TO ix_run_scenario_set_id")
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_test_case_result_test_case_id "
            "RENAME TO ix_scenario_result_scenario_id"
        )
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_test_case_result_run_id RENAME TO ix_scenario_result_run_id"
        )
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_test_case_result_passed RENAME TO ix_scenario_result_passed"
        )
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_eval_set_member_eval_set_id "
            "RENAME TO ix_scenario_set_member_scenario_set_id"
        )
    )
    op.execute(sa.text("ALTER INDEX ix_eval_set_name RENAME TO ix_scenario_set_name"))
    op.execute(sa.text("ALTER INDEX ix_test_case_agent_id RENAME TO ix_scenario_agent_id"))
    op.execute(sa.text("ALTER INDEX ix_test_case_tags_gin RENAME TO ix_scenario_tags_gin"))
    op.execute(sa.text("ALTER INDEX ix_test_case_status RENAME TO ix_scenario_status"))
    op.execute(sa.text("ALTER INDEX ix_test_case_difficulty RENAME TO ix_scenario_difficulty"))

    op.rename_table("test_case_result", "scenario_result")
    op.rename_table("eval_set_member", "scenario_set_member")
    op.rename_table("eval_set", "scenario_set")
    op.rename_table("test_case", "scenario")

    op.alter_column(
        "scenario_result",
        "test_case_id",
        new_column_name="scenario_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "run",
        "eval_set_version",
        new_column_name="scenario_set_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "run",
        "eval_set_id",
        new_column_name="scenario_set_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "scenario_set_member",
        "test_case_id",
        new_column_name="scenario_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "scenario_set_member",
        "eval_set_id",
        new_column_name="scenario_set_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )

    op.create_check_constraint(
        "ck_scenario_set_set_repetitions_ge_1",
        "scenario_set",
        "set_repetitions >= 1",
    )
    op.create_check_constraint(
        "ck_scenario_set_member_repetitions_ge_1",
        "scenario_set_member",
        "repetitions >= 1",
    )
    op.create_primary_key(
        "scenario_set_member_pkey",
        "scenario_set_member",
        ["scenario_set_id", "scenario_id"],
    )

    op.create_foreign_key(
        "scenario_result_scenario_id_fkey",
        "scenario_result",
        "scenario",
        ["scenario_id"],
        ["id"],
    )
    op.create_foreign_key(
        "scenario_set_member_scenario_set_id_fkey",
        "scenario_set_member",
        "scenario_set",
        ["scenario_set_id"],
        ["id"],
    )
    op.create_foreign_key(
        "scenario_set_member_scenario_id_fkey",
        "scenario_set_member",
        "scenario",
        ["scenario_id"],
        ["id"],
    )
    op.create_foreign_key(
        "run_scenario_set_id_fkey",
        "run",
        "scenario_set",
        ["scenario_set_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_scenario_agent_id_agent",
        "scenario",
        "agent",
        ["agent_id"],
        ["id"],
    )

    op.execute(sa.text("ALTER TYPE testcasestatus RENAME TO scenariostatus"))
