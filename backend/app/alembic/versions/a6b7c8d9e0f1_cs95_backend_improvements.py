"""CS-95 backend improvements: persona_context, first_turn, first_message,
drop max_turns and set_repetitions, expected_outcomes as list

Revision ID: a6b7c8d9e0f1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-15 12:00:00.000000

"""

import json

import sqlalchemy as sa

from alembic import op

revision = "a6b7c8d9e0f1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- test_case: add persona_context column --------------------------------
    op.add_column("test_case", sa.Column("persona_context", sa.Text(), nullable=True))

    # -- test_case: migrate persona JSONB → persona_context text --------------
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, persona FROM test_case WHERE persona IS NOT NULL")
    ).fetchall()
    for row_id, persona_raw in rows:
        if not persona_raw:
            continue
        p = persona_raw if isinstance(persona_raw, dict) else json.loads(persona_raw)
        parts = []
        if p.get("type"):
            parts.append(f"[Persona type]\n{p['type']}")
        if p.get("description"):
            parts.append(f"[Description]\n{p['description']}")
        if p.get("instructions"):
            parts.append(f"[Behavioral instructions]\n{p['instructions']}")
        context = "\n\n".join(parts)
        conn.execute(
            sa.text("UPDATE test_case SET persona_context = :ctx WHERE id = :id"),
            {"ctx": context, "id": row_id},
        )

    # -- test_case: drop persona column ---------------------------------------
    op.drop_column("test_case", "persona")

    # -- test_case: add first_turn enum column --------------------------------
    firstturn_enum = sa.Enum("AGENT", "PERSONA", name="firstturn")
    firstturn_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "test_case",
        sa.Column(
            "first_turn",
            firstturn_enum,
            nullable=False,
            server_default="PERSONA",
        ),
    )

    # -- test_case: rename initial_message → first_message --------------------
    op.alter_column("test_case", "initial_message", new_column_name="first_message")

    # -- test_case: drop max_turns --------------------------------------------
    op.drop_column("test_case", "max_turns")

    # -- test_case: migrate expected_outcomes dict → list ----------------------
    rows = conn.execute(
        sa.text(
            "SELECT id, expected_outcomes FROM test_case "
            "WHERE expected_outcomes IS NOT NULL"
        )
    ).fetchall()
    for row_id, outcomes_raw in rows:
        if not outcomes_raw:
            continue
        outcomes = (
            outcomes_raw
            if isinstance(outcomes_raw, dict)
            else json.loads(outcomes_raw)
        )
        if isinstance(outcomes, dict):
            statements: list[str] = []
            for k, v in outcomes.items():
                if isinstance(v, bool) and v:
                    statements.append(k.replace("_", " "))
                else:
                    statements.append(f"{k.replace('_', ' ')}: {v}")
            conn.execute(
                sa.text(
                    "UPDATE test_case SET expected_outcomes = CAST(:val AS jsonb) WHERE id = :id"
                ),
                {"val": json.dumps(statements), "id": row_id},
            )

    # -- eval_set: migrate set_repetitions into member repetitions ------------
    sets_with_reps = conn.execute(
        sa.text("SELECT id, set_repetitions FROM eval_set WHERE set_repetitions > 1")
    ).fetchall()
    for set_id, set_reps in sets_with_reps:
        conn.execute(
            sa.text(
                "UPDATE eval_set_member SET repetitions = repetitions * :mult "
                "WHERE eval_set_id = :sid"
            ),
            {"mult": set_reps, "sid": set_id},
        )

    # -- eval_set: drop set_repetitions column --------------------------------
    op.drop_column("eval_set", "set_repetitions")


def downgrade() -> None:
    # -- eval_set: restore set_repetitions ------------------------------------
    op.add_column(
        "eval_set",
        sa.Column(
            "set_repetitions",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # -- test_case: restore max_turns -----------------------------------------
    op.add_column(
        "test_case",
        sa.Column("max_turns", sa.Integer(), nullable=True),
    )

    # -- test_case: rename first_message → initial_message --------------------
    op.alter_column("test_case", "first_message", new_column_name="initial_message")

    # -- test_case: drop first_turn column and enum ---------------------------
    op.drop_column("test_case", "first_turn")
    sa.Enum(name="firstturn").drop(op.get_bind(), checkfirst=True)

    # -- test_case: restore persona column ------------------------------------
    op.add_column(
        "test_case",
        sa.Column("persona", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    # -- test_case: drop persona_context --------------------------------------
    op.drop_column("test_case", "persona_context")
