"""runtime mode config

Revision ID: u1v2w3x4y5z6
Revises: t9u0v1w2x3y4
Create Date: 2026-05-15

"""

from alembic import op

revision = "u1v2w3x4y5z6"
down_revision = "t9u0v1w2x3y4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            COALESCE(config, '{}'::jsonb),
            '{mode}',
            '"text"'::jsonb,
            true
        )
        """
    )
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            config,
            '{runtime}',
            CASE
                WHEN config ? 'runtime' THEN config->'runtime'
                WHEN config->'evaluation_engine'->>'kind' = 'custom_url'
                    THEN jsonb_build_object(
                        'kind', 'custom_endpoint',
                        'url', config->'evaluation_engine'->>'url'
                    )
                WHEN config->'evaluation_engine'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """
    )
    op.execute("UPDATE eval_config SET config = config - 'evaluation_engine'")

    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            COALESCE(config, '{}'::jsonb),
            '{mode}',
            '"text"'::jsonb,
            true
        )
        """
    )
    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            config,
            '{runtime}',
            CASE
                WHEN config ? 'runtime' THEN config->'runtime'
                WHEN config->'evaluation_engine'->>'kind' = 'custom_url'
                    THEN jsonb_build_object(
                        'kind', 'custom_endpoint',
                        'url', config->'evaluation_engine'->>'url'
                    )
                WHEN config->'evaluation_engine'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """
    )
    op.execute("UPDATE run SET config = config - 'evaluation_engine'")


def downgrade() -> None:
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            COALESCE(config, '{}'::jsonb) - 'mode' - 'runtime',
            '{evaluation_engine}',
            CASE
                WHEN config->'runtime'->>'kind' = 'custom_endpoint'
                    THEN jsonb_build_object(
                        'kind', 'custom_url',
                        'url', config->'runtime'->>'url'
                    )
                WHEN config->'runtime'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """
    )
    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            COALESCE(config, '{}'::jsonb) - 'mode' - 'runtime',
            '{evaluation_engine}',
            CASE
                WHEN config->'runtime'->>'kind' = 'custom_endpoint'
                    THEN jsonb_build_object(
                        'kind', 'custom_url',
                        'url', config->'runtime'->>'url'
                    )
                WHEN config->'runtime'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """
    )
