import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.services.usage_query import UsageQuery, calendar_month_start


class RollupService:
    @staticmethod
    async def get_usage_rollup(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        """
        Aggregate this tenant's metered usage and cost for the current billing
        window. Uses the same :class:`UsageQuery` helpers as
        :class:`QuotaService`, so ``GET /usage`` and quota enforcement can
        never report different numbers.

        The system invariant is that every tenant has a subscription row
        (seeded as ``free``/``active``). If it is genuinely missing, that is
        surfaced honestly (``plan_id="none"``, ``status="none"``) rather than
        being masked as an active free plan — matching the 402 that
        ``/generate`` would return for the same tenant.
        """
        subscription = (
            await db.execute(
                select(Subscription).where(Subscription.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

        if subscription is None:
            plan_id = "none"
            status = "none"
            period_start = calendar_month_start()
        else:
            plan_id = subscription.plan_id
            status = subscription.status
            period_start = subscription.current_period_start or calendar_month_start()

        api_calls = await UsageQuery.api_calls_used(db, tenant_id, period_start)
        tokens = await UsageQuery.token_breakdown(db, tenant_id, period_start)

        return {
            "tenant_id": str(tenant_id),
            "plan_id": plan_id,
            "status": status,
            "usage": {
                "api_calls": api_calls,
                "input_tokens": tokens["input_tokens"],
                "cached_input_tokens": tokens["cached_input_tokens"],
                "output_tokens": tokens["output_tokens"],
                "reasoning_tokens": tokens["reasoning_tokens"],
                "cost_microcents": tokens["cost_microcents"],
            },
        }
