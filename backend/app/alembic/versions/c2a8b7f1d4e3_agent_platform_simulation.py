"""agent platform simulation columns and run snapshot cleanup

Revision ID: c2a8b7f1d4e3
Revises: f1e2d3c4b5a6
Create Date: 2026-04-01 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c2a8b7f1d4e3"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column(
            "mode",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            server_default="endpoint",
            nullable=False,
        ),
    )
    op.add_column("agent", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column(
        "agent",
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "agent",
        sa.Column(
            "agent_model",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "agent_provider",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
    )
    op.alter_column(
        "agent",
        "endpoint_url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=2048),
        nullable=True,
    )

    op.add_column(
        "run",
        sa.Column(
            "agent_mode",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_model",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column(
            "agent_provider",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
    )
    op.drop_column("run", "prompt_snapshot")
    op.drop_column("run", "prompt_version")
    op.alter_column(
        "run",
        "agent_endpoint_url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=2048),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "run",
        "agent_endpoint_url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=2048),
        nullable=False,
    )
    op.add_column(
        "run",
        sa.Column(
            "prompt_version",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column("prompt_snapshot", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.drop_column("run", "agent_provider")
    op.drop_column("run", "agent_model")
    op.drop_column("run", "agent_mode")

    op.alter_column(
        "agent",
        "endpoint_url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=2048),
        nullable=False,
    )
    op.drop_column("agent", "agent_provider")
    op.drop_column("agent", "agent_model")
    op.drop_column("agent", "tools")
    op.drop_column("agent", "system_prompt")
    op.drop_column("agent", "mode")
