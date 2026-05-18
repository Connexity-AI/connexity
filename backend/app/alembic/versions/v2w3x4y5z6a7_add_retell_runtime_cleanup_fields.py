"""add retell runtime cleanup fields

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-05-18

"""

from alembic import op
import sqlalchemy as sa

revision = "v2w3x4y5z6a7"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_case_result",
        sa.Column("retell_chat_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "test_case_result",
        sa.Column("retell_chat_ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "test_case_result",
        sa.Column("retell_temp_chat_agent_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "test_case_result",
        sa.Column(
            "retell_temp_chat_agent_deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_test_case_result_retell_chat_id"),
        "test_case_result",
        ["retell_chat_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_test_case_result_retell_chat_id"), table_name="test_case_result")
    op.drop_column("test_case_result", "retell_temp_chat_agent_deleted_at")
    op.drop_column("test_case_result", "retell_temp_chat_agent_id")
    op.drop_column("test_case_result", "retell_chat_ended_at")
    op.drop_column("test_case_result", "retell_chat_id")
