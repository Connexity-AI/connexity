"""per-company predefined metrics

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-06-05

For every existing company, insert a per-tenant copy of every predefined
metric. The global predefined rows (company_id IS NULL) are soft-deleted so
they stop appearing in the per-company filtered queries — but kept in the DB
because historical eval configs may reference them by name and resolve via
``include_deleted=True``.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "z6a7b8c9d0e1"
down_revision = "y5z6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 0. The legacy global partial unique index (name) prevented two live rows
    #    with the same metric name from coexisting. That made sense when
    #    predefined metrics were singletons; now every tenant owns its own
    #    copy, so we need (company_id, name) uniqueness instead.
    op.execute("DROP INDEX IF EXISTS uq_custom_metric_name_active")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_custom_metric_company_name_active "
        "ON custom_metric (company_id, name) WHERE deleted_at IS NULL"
    )

    # 1. Per-company copies of the global predefined metrics.
    #
    # The Alembic seed migration (j7k8l9m0n1o2) inserted the canonical
    # predefined rows with company_id IS NULL. We replicate each of those
    # rows once per company so every tenant has its own toggleable copy.
    bind.execute(
        sa.text(
            """
            INSERT INTO custom_metric (
                id, company_id, name, display_name, description, tier,
                default_weight, score_type, rubric, include_in_defaults,
                is_predefined, is_draft, created_by, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                c.id,
                pm.name,
                pm.display_name,
                pm.description,
                pm.tier,
                pm.default_weight,
                pm.score_type,
                pm.rubric,
                pm.include_in_defaults,
                true,           -- is_predefined: still labeled "Built-in"
                pm.is_draft,
                NULL,
                now(),
                now()
            FROM company c
            CROSS JOIN custom_metric pm
            WHERE pm.is_predefined = true
              AND pm.company_id IS NULL
              AND pm.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM custom_metric existing
                  WHERE existing.company_id = c.id
                    AND existing.name = pm.name
                    AND existing.deleted_at IS NULL
              );
            """
        )
    )

    # 2. Soft-delete the global predefined rows so they stop appearing in
    #    per-company list queries. Keep them so historical eval configs that
    #    reference them by name can still resolve via include_deleted=True.
    bind.execute(
        sa.text(
            """
            UPDATE custom_metric
            SET deleted_at = :now
            WHERE is_predefined = true
              AND company_id IS NULL
              AND deleted_at IS NULL;
            """
        ),
        {"now": datetime.now(UTC)},
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Restore the legacy single-tenant uniqueness.
    op.execute("DROP INDEX IF EXISTS uq_custom_metric_company_name_active")
    op.execute(
        "CREATE UNIQUE INDEX uq_custom_metric_name_active "
        "ON custom_metric (name) WHERE deleted_at IS NULL"
    )

    # Re-activate the global predefined rows.
    bind.execute(
        sa.text(
            """
            UPDATE custom_metric
            SET deleted_at = NULL
            WHERE is_predefined = true
              AND company_id IS NULL;
            """
        )
    )

    # Drop the per-company copies (anything with company_id set + is_predefined).
    bind.execute(
        sa.text(
            """
            DELETE FROM custom_metric
            WHERE is_predefined = true
              AND company_id IS NOT NULL;
            """
        )
    )
