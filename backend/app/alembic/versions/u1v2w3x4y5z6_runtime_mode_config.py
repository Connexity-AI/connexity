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

NORMALIZED_CONFIG = """
CASE
    WHEN jsonb_typeof(config) = 'object' THEN config
    ELSE '{}'::jsonb
END
"""


def upgrade() -> None:
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            __CONFIG__,
            '{mode}',
            '"text"'::jsonb,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            __CONFIG__,
            '{runtime}',
            CASE
                WHEN __CONFIG__ ? 'runtime' THEN __CONFIG__->'runtime'
                WHEN __CONFIG__->'evaluation_engine'->>'kind' = 'custom_url'
                    THEN jsonb_build_object(
                        'kind', 'custom_endpoint',
                        'url', __CONFIG__->'evaluation_engine'->>'url'
                    )
                WHEN __CONFIG__->'evaluation_engine'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
    op.execute(
        """
        UPDATE eval_config
        SET config = __CONFIG__ - 'evaluation_engine'
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )

    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            __CONFIG__,
            '{mode}',
            '"text"'::jsonb,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            __CONFIG__,
            '{runtime}',
            CASE
                WHEN __CONFIG__ ? 'runtime' THEN __CONFIG__->'runtime'
                WHEN __CONFIG__->'evaluation_engine'->>'kind' = 'custom_url'
                    THEN jsonb_build_object(
                        'kind', 'custom_endpoint',
                        'url', __CONFIG__->'evaluation_engine'->>'url'
                    )
                WHEN __CONFIG__->'evaluation_engine'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
    op.execute(
        """
        UPDATE run
        SET config = __CONFIG__ - 'evaluation_engine'
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE eval_config
        SET config = jsonb_set(
            __CONFIG__ - 'mode' - 'runtime',
            '{evaluation_engine}',
            CASE
                WHEN __CONFIG__->'runtime'->>'kind' = 'custom_endpoint'
                    THEN jsonb_build_object(
                        'kind', 'custom_url',
                        'url', __CONFIG__->'runtime'->>'url'
                    )
                WHEN __CONFIG__->'runtime'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
    op.execute(
        """
        UPDATE run
        SET config = jsonb_set(
            __CONFIG__ - 'mode' - 'runtime',
            '{evaluation_engine}',
            CASE
                WHEN __CONFIG__->'runtime'->>'kind' = 'custom_endpoint'
                    THEN jsonb_build_object(
                        'kind', 'custom_url',
                        'url', __CONFIG__->'runtime'->>'url'
                    )
                WHEN __CONFIG__->'runtime'->>'kind' = 'retell'
                    THEN '{"kind":"retell"}'::jsonb
                ELSE '{"kind":"connexity"}'::jsonb
            END,
            true
        )
        """.replace("__CONFIG__", NORMALIZED_CONFIG)
    )
