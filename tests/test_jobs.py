import logging

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.jobs.runner import run_job
from app.models.job_run import JobRun
from app.models.tenant import Tenant
from app.models.subscription import Subscription


@pytest.fixture
def session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_run_job_records_success(session_factory):
    calls = []

    async def body(session):
        calls.append(1)
        return {"synced": 3}

    result = await run_job(
        "unit_success_job", body, attempts=3, base_delay=0, session_factory=session_factory
    )

    assert result == {"synced": 3}
    assert len(calls) == 1  # succeeded first try, no retries

    async with session_factory() as s:
        row = (
            await s.execute(select(JobRun).where(JobRun.job_name == "unit_success_job"))
        ).scalar_one()
    assert row.status == "success"
    assert row.attempts == 1
    assert row.finished_at is not None
    assert row.error is None


@pytest.mark.asyncio
async def test_run_job_retries_then_alerts(session_factory, caplog):
    attempts_seen = []

    async def flaky(session):
        attempts_seen.append(1)
        raise RuntimeError("stripe unreachable")

    with caplog.at_level(logging.CRITICAL, logger="app.jobs"):
        result = await run_job(
            "unit_failing_job", flaky, attempts=3, base_delay=0,
            session_factory=session_factory,
        )

    assert result is None
    assert len(attempts_seen) == 3  # retried up to the limit

    async with session_factory() as s:
        row = (
            await s.execute(select(JobRun).where(JobRun.job_name == "unit_failing_job"))
        ).scalar_one()
    assert row.status == "failed"
    assert row.attempts == 3
    assert row.finished_at is not None
    assert "stripe unreachable" in (row.error or "")

    # The "failure alert": a CRITICAL log line once retries are exhausted.
    assert any(
        rec.levelno == logging.CRITICAL and "JOB FAILURE ALERT" in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_admin_reconcile_endpoint_records_job_run(db: AsyncSession, client):
    """POST /admin/jobs/reconcile runs the sweep now and records a job_runs row."""
    tenant = Tenant(name="Admin Job Tenant")
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    db.add(Subscription(tenant_id=tenant.id, plan_id="free", status="active"))
    await db.commit()

    empty = MagicMock()
    empty.data = []
    with patch("stripe.Subscription.list", return_value=empty):
        resp = await client.post("/admin/jobs/reconcile")

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_name"] == "stripe_reconciliation"
    assert body["status"] == "success"

    listed = await client.get("/admin/jobs")
    assert listed.status_code == 200
    assert any(r["status"] == "success" for r in listed.json())
