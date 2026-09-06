import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_event import UsageEvent


def calendar_month_start(now: datetime | None = None) -> datetime:
    """First instant of the current UTC calendar month."""
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class UsageQuery:
    """
    Single source of truth for "how much has this tenant used since
    ``period_start``".  Both :class:`QuotaService` (enforcement, before the
    action) and :class:`RollupService` (reporting, GET /usage) call these
    helpers, so the two can never disagree about the numbers.

    Billable-call accounting
    ------------------------
    ``POST /generate`` writes **exactly one** ``usage_event`` per call
    (``type='ai_token'``).  That single row counts as *1 API call* against the
    API-call quota **and** as *N tokens* against the token quota.  Standalone
    ``type='api_call'`` rows (``quantity >= 1``) are also supported and add
    their ``quantity`` to the API-call total — used by bulk/administrative
    metering paths and covered by ``tests/test_metering.py``.
    """

    @staticmethod
    async def api_calls_used(
        db: AsyncSession, tenant_id: uuid.UUID, period_start: datetime
    ) -> int:
        api_call_qty = select(
            func.coalesce(func.sum(UsageEvent.quantity), 0)
        ).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.type == "api_call",
            UsageEvent.created_at >= period_start,
        )
        generate_rows = select(func.count(UsageEvent.id)).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.type == "ai_token",
            UsageEvent.created_at >= period_start,
        )
        a = (await db.execute(api_call_qty)).scalar() or 0
        b = (await db.execute(generate_rows)).scalar() or 0
        return int(a) + int(b)

    @staticmethod
    async def tokens_used(
        db: AsyncSession, tenant_id: uuid.UUID, period_start: datetime
    ) -> int:
        stmt = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.type == "ai_token",
            UsageEvent.created_at >= period_start,
        )
        return int((await db.execute(stmt)).scalar() or 0)

    @staticmethod
    async def token_breakdown(
        db: AsyncSession, tenant_id: uuid.UUID, period_start: datetime
    ) -> dict:
        stmt = select(
            func.coalesce(func.sum(UsageEvent.token_input), 0),
            func.coalesce(func.sum(UsageEvent.token_cached_input), 0),
            func.coalesce(func.sum(UsageEvent.token_output), 0),
            func.coalesce(func.sum(UsageEvent.token_reasoning), 0),
            func.coalesce(func.sum(UsageEvent.cost_microcents), 0),
        ).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.type == "ai_token",
            UsageEvent.created_at >= period_start,
        )
        row = (await db.execute(stmt)).first()
        return {
            "input_tokens": int(row[0] or 0),
            "cached_input_tokens": int(row[1] or 0),
            "output_tokens": int(row[2] or 0),
            "reasoning_tokens": int(row[3] or 0),
            "cost_microcents": int(row[4] or 0),
        }
