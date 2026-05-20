"""add voice_simulation_job table

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-05-20

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "v2w3x4y5z6a7"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_simulation_job",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_result_id", sa.Uuid(), nullable=False),
        sa.Column("repetition_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dtmf_code", sa.String(length=16), nullable=False),
        sa.Column("agent_phone_number", sa.String(length=32), nullable=False),
        sa.Column("stt_provider", sa.String(length=64), nullable=False),
        sa.Column("stt_model", sa.String(length=255), nullable=False),
        sa.Column("tts_provider", sa.String(length=64), nullable=False),
        sa.Column("tts_model", sa.String(length=255), nullable=False),
        sa.Column("tts_voice_id", sa.String(length=255), nullable=False),
        sa.Column("twilio_call_sid", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("call_started_at", sa.DateTime(), nullable=True),
        sa.Column("call_ended_at", sa.DateTime(), nullable=True),
        sa.Column("result_received_at", sa.DateTime(), nullable=True),
        sa.Column("audio_url", sa.String(length=2048), nullable=True),
        sa.Column("submitted_messages", JSONB(), nullable=True),
        sa.Column("normalized_transcript", JSONB(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_case.id"]),
        sa.ForeignKeyConstraint(["test_case_result_id"], ["test_case_result.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_voice_simulation_job_run_id"),
        "voice_simulation_job",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_test_case_id"),
        "voice_simulation_job",
        ["test_case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_test_case_result_id"),
        "voice_simulation_job",
        ["test_case_result_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_status"),
        "voice_simulation_job",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_dtmf_code"),
        "voice_simulation_job",
        ["dtmf_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_twilio_call_sid"),
        "voice_simulation_job",
        ["twilio_call_sid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_simulation_job_lease_expires_at"),
        "voice_simulation_job",
        ["lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_voice_simulation_job_lease_expires_at"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_twilio_call_sid"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_dtmf_code"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_status"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_test_case_result_id"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_test_case_id"),
        table_name="voice_simulation_job",
    )
    op.drop_index(
        op.f("ix_voice_simulation_job_run_id"),
        table_name="voice_simulation_job",
    )
    op.drop_table("voice_simulation_job")
