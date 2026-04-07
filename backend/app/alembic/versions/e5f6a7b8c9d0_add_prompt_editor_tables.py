"""add prompt_editor_session and prompt_editor_message tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-07 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_editor_session",
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_editor_session_agent_id"),
        "prompt_editor_session",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prompt_editor_session_created_by"),
        "prompt_editor_session",
        ["created_by"],
        unique=False,
    )

    op.create_table(
        "prompt_editor_message",
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_suggestion", sa.Text(), nullable=True),
        sa.Column("suggestion_status", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["prompt_editor_session.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_editor_message_session_id"),
        "prompt_editor_message",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_prompt_editor_message_session_id"),
        table_name="prompt_editor_message",
    )
    op.drop_table("prompt_editor_message")
    op.drop_index(
        op.f("ix_prompt_editor_session_created_by"),
        table_name="prompt_editor_session",
    )
    op.drop_index(
        op.f("ix_prompt_editor_session_agent_id"),
        table_name="prompt_editor_session",
    )
    op.drop_table("prompt_editor_session")
