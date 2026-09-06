"""
Generic background-job runner: retries + a durable ``job_runs`` record + a
CRITICAL "failure alert" log line when a job is finally exhausted.

The job body is any ``async def body(session) -> Any``. It receives a fresh
:class:`AsyncSession` per attempt and must be safe to retry (idempotent). The
runner owns the transaction boundary and commits on success.
"""
import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_maker
from app.models.job_run import JobRun

logger = logging.getLogger("app.jobs")

JobBody = Callable[[AsyncSession], Awaitable[object]]


async def run_job(
    job_name: str,
    body: JobBody,
    *,
    attempts: int = 3,
    base_delay: float = 2.0,
    session_factory: Optional[async_sessionmaker] = None,
) -> Optional[object]:
    """
    Run ``body`` up to ``attempts`` times with linear back-off. Records exactly
    one ``job_runs`` row (``running`` -> ``success`` | ``failed``). Never raises:
    a scheduler thread must survive a failing job.
    """
    factory = session_factory or async_session_maker

    async with factory() as session:
        job_run = JobRun(job_name=job_name, status="running", attempts=0)
        session.add(job_run)
        await session.commit()
        await session.refresh(job_run)
        job_run_id = job_run.id

    last_err: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            async with factory() as session:
                result = await body(session)
                await session.commit()
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning(
                "job %s: attempt %d/%d failed: %s", job_name, attempt, attempts, e
            )
            if attempt < attempts:
                await asyncio.sleep(base_delay * attempt)
            continue

        async with factory() as session:
            jr = await session.get(JobRun, job_run_id)
            jr.status = "success"
            jr.attempts = attempt
            jr.finished_at = datetime.now(timezone.utc)
            await session.commit()
        logger.info(
            "job %s: succeeded on attempt %d/%d (%s)", job_name, attempt, attempts, result
        )
        return result

    # Exhausted — persist the failure and raise the alert.
    async with factory() as session:
        jr = await session.get(JobRun, job_run_id)
        jr.status = "failed"
        jr.attempts = attempts
        jr.finished_at = datetime.now(timezone.utc)
        jr.error = "".join(
            traceback.format_exception(type(last_err), last_err, last_err.__traceback__)
        )[:4000]
        await session.commit()

    logger.critical(
        "JOB FAILURE ALERT: %s failed after %d attempt(s): %s",
        job_name,
        attempts,
        last_err,
    )
    return None
