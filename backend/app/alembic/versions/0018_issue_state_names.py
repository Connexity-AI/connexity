"""issue states: regressed becomes reopened, accepted becomes archived

Revision ID: 0018_issue_state_names
Revises: 0017_categories
Create Date: 2026-11-13 18:30:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0018_issue_state_names'
down_revision = '0017_categories'
branch_labels = None
depends_on = None

# Dmytro renamed the states on 2026-11-12. Decision records keep the state they
# recorded, so they are renamed too.
RENAMES = [("regressed", "reopened"), ("accepted", "archived")]


def _rename(pairs: list[tuple[str, str]]) -> None:
    for old, new in pairs:
        op.execute(f"UPDATE issue SET state = '{new}' WHERE state = '{old}'")
        for column in ("old_value", "new_value"):
            op.execute(
                f"UPDATE decision_record SET {column} = '{new}' "
                f"WHERE kind = 'issue_state' AND {column} = '{old}'"
            )


def upgrade():
    _rename(RENAMES)


def downgrade():
    _rename([(new, old) for old, new in RENAMES])
