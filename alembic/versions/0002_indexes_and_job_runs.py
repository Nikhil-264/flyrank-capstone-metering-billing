"""usage_events lookup index + job_runs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index backing every quota check and usage rollup
    # (app/services/usage_query.py filters on exactly these columns).
    op.create_index(
        "ix_usage_events_tenant_type_created",
        "usage_events",
        ["tenant_id", "type", "created_at"],
    )

    # Durable execution log for background jobs (the scheduler's observability
    # + persistent failure-alert surface).
    op.create_table(
        "job_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_runs_job_name_started", "job_runs", ["job_name", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_job_runs_job_name_started", table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_index("ix_usage_events_tenant_type_created", table_name="usage_events")
