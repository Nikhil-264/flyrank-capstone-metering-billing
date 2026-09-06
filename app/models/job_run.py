import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JobRun(Base):
    """
    One execution of a background job. This table is the durable record that
    makes the scheduler observable: a demo/evaluator can query it, and a
    ``status='failed'`` row is the persistent half of the failure alert
    (the other half is a CRITICAL log line — see app/jobs/runner.py).
    """

    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # running | success | failed
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_job_runs_job_name_started", "job_name", "started_at"),
    )
