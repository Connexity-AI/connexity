"""add company multitenancy

Revision ID: y5z6a7b8c9d0
Revises: e8f9a0b1c2d3, x3y4z5a6b7c8
Create Date: 2026-06-04

Multi-tenancy lives at the merge of the two pre-existing heads in the
migration graph (``e8f9a0b1c2d3`` from the integrations + call-soft-delete
chain and ``x3y4z5a6b7c8`` from the call-label branch). Merging at the
multitenancy revision avoids a no-op merge migration before it.
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "y5z6a7b8c9d0"
down_revision: tuple[str, str] = ("e8f9a0b1c2d3", "x3y4z5a6b7c8")
branch_labels = None
depends_on = None


# Tables that get a NOT NULL company_id column.
_SCOPED_TABLES: list[str] = [
    "user",
    "agent",
    "agent_version",
    "run",
    "call",
    "prompt_editor_session",
    "prompt_editor_message",
    "deployment",
    "environment",
    "integration",
    "eval_config",
    "eval_config_member",
    "test_case",
    "test_case_result",
    "oauth_authorization_code",
    "oauth_refresh_token",
]


def upgrade() -> None:
    # 1. Create company table.
    op.create_table(
        "company",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 2. Insert the single legacy company and capture its id.
    bind = op.get_bind()
    legacy_id = uuid.uuid4()
    bind.execute(
        sa.text("INSERT INTO company (id) VALUES (:id)"),
        {"id": str(legacy_id)},
    )

    # 3. Add nullable company_id to all scoped tables, backfill, then lock NOT NULL.
    for table in _SCOPED_TABLES:
        op.add_column(
            table,
            sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        bind.execute(
            sa.text(f'UPDATE "{table}" SET company_id = :cid'),
            {"cid": str(legacy_id)},
        )
        op.alter_column(table, "company_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_company_id",
            table,
            "company",
            ["company_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(
            f"ix_{table}_company_id",
            table,
            ["company_id"],
        )

    # 4. custom_metric: company_id stays NULLABLE because predefined system
    #    metrics have no owning company.
    op.add_column(
        "custom_metric",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    bind.execute(
        sa.text(
            "UPDATE custom_metric SET company_id = :cid "
            "WHERE is_predefined = false"
        ),
        {"cid": str(legacy_id)},
    )
    op.create_foreign_key(
        "fk_custom_metric_company_id",
        "custom_metric",
        "company",
        ["company_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_custom_metric_company_id",
        "custom_metric",
        ["company_id"],
    )


def downgrade() -> None:
    for table in _SCOPED_TABLES + ["custom_metric"]:
        op.drop_index(f"ix_{table}_company_id", table_name=table)
        op.drop_constraint(f"fk_{table}_company_id", table, type_="foreignkey")
        op.drop_column(table, "company_id")

    op.drop_table("company")
