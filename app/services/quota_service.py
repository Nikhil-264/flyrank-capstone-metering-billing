import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.plan import Plan
from app.api.errors import QuotaExceededException, PaymentRequiredException
from app.services.usage_query import UsageQuery, calendar_month_start


def _seconds_until_reset(period_end: datetime | None) -> int:
    """Seconds until the quota window resets (Retry-After hint)."""
    now = datetime.now(timezone.utc)
    if period_end is not None:
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        if period_end > now:
            return int((period_end - now).total_seconds())
    # Fall back to the first instant of next calendar month.
    year, month = now.year, now.month
    nxt = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=timezone.utc)
    return int((nxt - now).total_seconds())


class QuotaService:
    @staticmethod
    async def check_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        requested_tokens: int,
    ) -> None:
        """
        Enforce the tenant's plan allowance *before* the action is recorded.

        - Raises :class:`PaymentRequiredException` (402) when there is no
          subscription or the subscription is not ``active``.
        - Raises :class:`QuotaExceededException` (429), with a ``Retry-After``
          hint, when the API-call or token allowance would be exceeded.

        Concurrency: the tenant's subscription row is locked ``FOR UPDATE`` for
        the life of the request transaction, so two simultaneous ``/generate``
        calls for the same tenant are serialized here and cannot both slip
        past the boundary check. See ``rules/quota-and-status-codes.md``.
        """
        # 1. Load + lock the subscription row (serializes concurrent requests
        #    for this tenant until the caller commits or rolls back).
        sub_stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .with_for_update()
        )
        subscription = (await db.execute(sub_stmt)).scalar_one_or_none()

        if subscription is None:
            raise PaymentRequiredException(
                message="No active subscription found for this tenant. Please subscribe to a plan to continue."
            )

        if subscription.status != "active":
            raise PaymentRequiredException(
                message=(
                    f"Active subscription required. Plan is currently "
                    f"'{subscription.status}'. Please upgrade or pay your "
                    f"outstanding invoice to resume."
                )
            )

        plan = (
            await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
        ).scalar_one_or_none()
        if plan is None:
            raise PaymentRequiredException(
                message="Subscription references an unknown plan. Please contact support."
            )

        # 2. Billing-cycle start: Stripe's current_period_start when known,
        #    otherwise the first day of the current calendar month.
        period_start = subscription.current_period_start or calendar_month_start()
        retry_after = _seconds_until_reset(subscription.current_period_end)

        # 3. Current usage in this window (shared with RollupService).
        current_api_calls = await UsageQuery.api_calls_used(db, tenant_id, period_start)
        current_tokens = await UsageQuery.tokens_used(db, tenant_id, period_start)

        # 4. Boundary rule: allow iff current + requested <= limit.
        if current_api_calls + 1 > plan.max_api_calls:
            raise QuotaExceededException(
                message=(
                    f"Usage quota exceeded. Monthly limit is {plan.max_api_calls:,} "
                    f"API calls, current usage is {current_api_calls:,} API calls, "
                    f"requested 1 API call."
                ),
                retry_after=retry_after,
            )

        if requested_tokens > 0 and (current_tokens + requested_tokens > plan.max_tokens):
            raise QuotaExceededException(
                message=(
                    f"Usage quota exceeded. Monthly limit is {plan.max_tokens:,} "
                    f"AI tokens, current usage is {current_tokens:,} AI tokens, "
                    f"requested {requested_tokens:,} tokens."
                ),
                retry_after=retry_after,
            )
