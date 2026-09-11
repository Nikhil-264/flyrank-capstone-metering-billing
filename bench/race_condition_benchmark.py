"""
Real before/after benchmark for the FOR UPDATE quota-boundary fix.

For N trials: seed a tenant sitting at 999/1000 API calls, then fire two
truly concurrent boundary requests at it.
  - "before" mode calls check_quota_UNSAFE (identical logic, minus
    .with_for_update() -- i.e. the pre-hardening code path).
  - "after" mode calls the real QuotaService.check_quota (with the lock).
Report the % of trials where BOTH requests were allowed (an overcount:
the tenant ends up at 1001/1000 instead of the correct 1000/1000).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.models.base import Base
import app.models  # noqa: register all tables
from app.db.seed import seed_plans
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.usage_event import UsageEvent
from app.models.plan import Plan
from app.api.errors import QuotaExceededException, PaymentRequiredException
from app.services.usage_query import UsageQuery, calendar_month_start
from app.services.meter_service import MeterService

TRIALS = 40


async def check_quota_unsafe(db, tenant_id, requested_tokens):
    """Identical to QuotaService.check_quota but WITHOUT the FOR UPDATE lock --
    i.e. exactly the pre-hardening code path this project shipped before the
    concurrency fix."""
    sub_stmt = select(Subscription).where(Subscription.tenant_id == tenant_id)  # no .with_for_update()
    subscription = (await db.execute(sub_stmt)).scalar_one_or_none()
    if subscription is None or subscription.status != "active":
        raise PaymentRequiredException("no active subscription")
    plan = (await db.execute(select(Plan).where(Plan.id == subscription.plan_id))).scalar_one_or_none()
    period_start = subscription.current_period_start or calendar_month_start()
    current_api_calls = await UsageQuery.api_calls_used(db, tenant_id, period_start)
    if current_api_calls + 1 > plan.max_api_calls:
        raise QuotaExceededException("quota exceeded")


async def run_trial(session_factory, unsafe: bool):
    period_start = datetime.now(timezone.utc) - timedelta(days=1)
    async with session_factory() as s:
        tenant = Tenant(name=f"bench-{uuid.uuid4().hex[:8]}")
        s.add(tenant)
        await s.commit()
        await s.refresh(tenant)
        tid = tenant.id
        s.add(Subscription(tenant_id=tid, plan_id="free", status="active",
                           current_period_start=period_start,
                           current_period_end=datetime.now(timezone.utc) + timedelta(days=29)))
        for i in range(999):
            s.add(UsageEvent(tenant_id=tid, type="api_call", quantity=1,
                             idempotency_key=f"fill-{i}", cost_microcents=0))
        await s.commit()

    async def attempt(key):
        async with session_factory() as session:
            if unsafe:
                await check_quota_unsafe(session, tid, 1)
            else:
                from app.services.quota_service import QuotaService
                await QuotaService.check_quota(session, tid, 1)
            await MeterService.record(db=session, tenant_id=tid, type="ai_token",
                                      quantity=1, idempotency_key=key, token_input=1)
            await session.commit()

    results = await asyncio.gather(attempt("race-a"), attempt("race-b"), return_exceptions=True)
    successes = sum(1 for r in results if r is None)

    async with session_factory() as s:
        total = await s.scalar(select(func.count(UsageEvent.id)).where(UsageEvent.tenant_id == tid))
    overcounted = total > 1000
    return successes, total, overcounted


async def run_mode(session_factory, unsafe: bool, label: str):
    overcounts = 0
    for i in range(TRIALS):
        successes, total, overcounted = await run_trial(session_factory, unsafe)
        overcounts += int(overcounted)
    rate = 100.0 * overcounts / TRIALS
    print(f"{label}: {overcounts}/{TRIALS} trials overcounted the 1000-call boundary "
          f"({rate:.1f}%)")
    return rate


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        await seed_plans(s)
        await s.commit()

    print(f"Running {TRIALS} concurrent-boundary trials per mode ...\n")
    before_rate = await run_mode(session_factory, unsafe=True, label="BEFORE (no FOR UPDATE lock)")
    after_rate = await run_mode(session_factory, unsafe=False, label="AFTER  (FOR UPDATE lock)")

    print(f"\n=== RESULT: quota-boundary overcount rate under concurrent load: "
          f"{before_rate:.1f}% -> {after_rate:.1f}% after adding the row lock "
          f"({TRIALS} trials/mode) ===")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
