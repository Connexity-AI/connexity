"""add custom_metric table and run.created_by

Revision ID: f1e2d3c4b5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "f1e2d3c4b5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tier_enum = sa.Enum(
        "execution",
        "knowledge",
        "process",
        "delivery",
        name="metrictier",
    )
    score_enum = sa.Enum("scored", "binary", name="scoretype")

    op.create_table(
        "custom_metric",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tier", tier_enum, nullable=False),
        sa.Column("default_weight", sa.Float(), nullable=False),
        sa.Column("score_type", score_enum, nullable=False),
        sa.Column("rubric", sa.Text(), nullable=False),
        sa.Column("include_in_defaults", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
            ["created_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by", "name", name="uq_custom_metric_owner_name"),
    )
    op.create_index(
        op.f("ix_custom_metric_created_by"), "custom_metric", ["created_by"], unique=False
    )

    op.add_column("run", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_run_created_by"), "run", ["created_by"], unique=False)
    op.create_foreign_key(
        "fk_run_created_by_user",
        "run",
        "user",
        ["created_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_run_created_by_user", "run", type_="foreignkey")
    op.drop_index(op.f("ix_run_created_by"), table_name="run")
    op.drop_column("run", "created_by")

    op.drop_index(op.f("ix_custom_metric_created_by"), table_name="custom_metric")
    op.drop_table("custom_metric")

    sa.Enum(name="scoretype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="metrictier").drop(op.get_bind(), checkfirst=True)
