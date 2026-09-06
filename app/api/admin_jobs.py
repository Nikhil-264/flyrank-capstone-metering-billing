"""
Admin surface for the background-job machinery — lets a demo/evaluator trigger
the reconciliation sweep on demand and inspect recent runs without waiting for
03:00 UTC.

Scope note: like the rest of this capstone there is no real authorization here
(see docs/architecture.md "Security scope"). In a real deployment these routes
would sit behind an admin role.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job_run import JobRun
from app.services.reconciliation_service import (
    RECONCILIATION_JOB_NAME as RECONCILIATION_JOB,
    reconcile_from_stripe,
)

router = APIRouter(prefix="/admin/jobs")
logger = logging.getLogger("app.api.admin_jobs")


class JobRunOut(BaseModel):
    id: str
    job_name: str
    status: str
    attempts: int
    started_at: str
    finished_at: str | None
    error: str | None


def _serialize(jr: JobRun) -> JobRunOut:
    return JobRunOut(
        id=str(jr.id),
        job_name=jr.job_name,
        status=jr.status,
        attempts=jr.attempts,
        started_at=jr.started_at.isoformat() if jr.started_at else "",
        finished_at=jr.finished_at.isoformat() if jr.finished_at else None,
        error=jr.error,
    )


@router.get("", response_model=list[JobRunOut])
async def list_job_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(JobRun).order_by(JobRun.started_at.desc()).limit(min(limit, 100))
        )
    ).scalars().all()
    return [_serialize(r) for r in rows]


@router.post("/reconcile", response_model=JobRunOut)
async def trigger_reconciliation(db: AsyncSession = Depends(get_db)):
    """
    Run the Stripe reconciliation sweep now, synchronously, and record a
    ``job_runs`` row. Retries live in the scheduled path
    (:func:`app.jobs.runner.run_job`); this on-demand trigger is single-shot.
    """
    jr = JobRun(job_name=RECONCILIATION_JOB, status="running", attempts=1)
    db.add(jr)
    await db.commit()
    await db.refresh(jr)

    try:
        summary = await reconcile_from_stripe(db)
        await db.commit()
        jr.status = "success"
        jr.finished_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("manual reconciliation ok: %s", summary)
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        jr.status = "failed"
        jr.finished_at = datetime.now(timezone.utc)
        jr.error = str(e)[:4000]
        await db.commit()
        logger.critical("JOB FAILURE ALERT: manual %s failed: %s", RECONCILIATION_JOB, e)

    await db.refresh(jr)
    return _serialize(jr)
