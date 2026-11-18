"""onboarding's finish line: when a workspace first completed it, and answers the
assistant proposed and the person confirmed

Revision ID: 0034_onboarding_completed
Revises: 0033_model_checks
Create Date: 2026-11-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0034_onboarding_completed'
down_revision = '0033_model_checks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'company',
        sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    # A workspace past its first scan today keeps its score: it counts as complete
    # from then (plan `plans/2026-11-18-onboarding-ends-with-dashboard.md`, Risks).
    op.execute(
        "UPDATE company SET onboarding_completed_at = first_scan_done_at "
        "WHERE first_scan_done_at IS NOT NULL"
    )
    op.add_column(
        'clarification',
        sa.Column(
            'answer_proposed', sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column('clarification', 'answer_proposed')
    op.drop_column('company', 'onboarding_completed_at')
