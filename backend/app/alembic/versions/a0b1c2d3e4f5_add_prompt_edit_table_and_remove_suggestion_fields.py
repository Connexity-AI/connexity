"""add prompt_edit table; drop prompt_suggestion and suggestion_status

Revision ID: a0b1c2d3e4f5
Revises: e5f6a7b8c9d0
Create Date: 2026-04-10 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_edit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("new_content", sa.Text(), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["prompt_editor_message.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_edit_message_id"),
        "prompt_edit",
        ["message_id"],
        unique=False,
    )

    op.drop_column("prompt_editor_message", "prompt_suggestion")
    op.drop_column("prompt_editor_message", "suggestion_status")


def downgrade() -> None:
    op.add_column(
        "prompt_editor_message",
        sa.Column("suggestion_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "prompt_editor_message",
        sa.Column("prompt_suggestion", sa.Text(), nullable=True),
    )

    op.drop_index(
        op.f("ix_prompt_edit_message_id"),
        table_name="prompt_edit",
    )
    op.drop_table("prompt_edit")
