"""
APScheduler wiring. Started from the FastAPI lifespan (app/main.py) when
``ENABLE_SCHEDULER`` is true; disabled automatically under pytest.

Currently one job: a nightly Stripe reconciliation sweep at 03:00 UTC, run
through :func:`app.jobs.runner.run_job` so it gets retries, a durable
``job_runs`` record, and a CRITICAL failure alert.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.runner import run_job
from app.services.reconciliation_service import (
    RECONCILIATION_JOB_NAME as RECONCILIATION_JOB,
    reconcile_from_stripe,
)

logger = logging.getLogger("app.jobs.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def run_reconciliation_job() -> None:
    await run_job(RECONCILIATION_JOB, reconcile_from_stripe, attempts=3)


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_reconciliation_job,
        CronTrigger(hour=3, minute=0),
        id=RECONCILIATION_JOB,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "APScheduler started: %s scheduled nightly at 03:00 UTC", RECONCILIATION_JOB
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler stopped")
