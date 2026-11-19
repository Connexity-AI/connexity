"""Every run of scenarios has a version: the runs stored without one are deleted with
their simulated calls and verdicts, and a check keeps it so

Revision ID: 0039_runs_have_a_version
Revises: 0038_feedback_report
Create Date: 2026-11-19 18:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0039_runs_have_a_version'
down_revision = '0038_feedback_report'
branch_labels = None
depends_on = None

_NO_VERSION = "SELECT id FROM run WHERE scope IS NOT NULL AND platform_version IS NULL"


def upgrade() -> None:
    # Dmytro, 2026-11-19: "Runs with no version stored are deleted". Verdicts go with
    # their run (cascade); simulated calls have no cascade, so they go first.
    op.execute(f"DELETE FROM rule_verdict WHERE run_id IN ({_NO_VERSION})")
    op.execute(f"DELETE FROM test_case_result WHERE run_id IN ({_NO_VERSION})")
    op.execute(f"DELETE FROM run WHERE id IN ({_NO_VERSION})")
    op.create_check_constraint(
        'ck_run_scenarios_have_a_version',
        'run',
        'scope IS NULL OR platform_version IS NOT NULL',
    )


def downgrade() -> None:
    op.drop_constraint('ck_run_scenarios_have_a_version', 'run', type_='check')
