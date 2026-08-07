import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.usage_event import UsageEvent
from app.api.errors import QuotaExceededException, PaymentRequiredException

class QuotaService:
    @staticmethod
    async def check_quota(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        requested_tokens: int
    ) -> None:
        """
        Check if the tenant has enough quota to proceed with the action.
        Raises PaymentRequiredException (402) if subscription is canceled/inactive.
        Raises QuotaExceededException (429) if limits are exceeded.
        """
        # 1. Fetch Subscription and Plan
        stmt = (
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .filter(Subscription.tenant_id == tenant_id)
        )
        res = await db.execute(stmt)
        row = res.first()
        
        if not row:
            raise PaymentRequiredException(
                message="No active subscription found for this tenant. Please subscribe to a plan to continue."
            )

        subscription, plan = row

        # Check subscription status
        if subscription.status != "active":
            raise PaymentRequiredException(
                message=f"Active subscription required. Plan is currently '{subscription.status}'. Please upgrade or pay your outstanding invoice to resume."
            )

        # 2. Determine billing cycle start
        # Default to the first day of the current month if current_period_start is not set
        period_start = subscription.current_period_start
        if not period_start:
            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 3. Query current usage in this billing period
        # Count API calls: sum quantity of type 'api_call' + count of events of type 'ai_token'
        api_calls_sum_stmt = (
            select(func.sum(UsageEvent.quantity))
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.type == "api_call",
                UsageEvent.created_at >= period_start
            )
        )
        api_calls_sum_res = await db.execute(api_calls_sum_stmt)
        api_calls_sum = api_calls_sum_res.scalar() or 0

        ai_tokens_count_stmt = (
            select(func.count(UsageEvent.id))
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.type == "ai_token",
                UsageEvent.created_at >= period_start
            )
        )
        ai_tokens_count_res = await db.execute(ai_tokens_count_stmt)
        ai_tokens_count = ai_tokens_count_res.scalar() or 0

        current_api_calls = api_calls_sum + ai_tokens_count

        # Count AI tokens
        tokens_stmt = (
            select(func.sum(UsageEvent.quantity))
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.type == "ai_token",
                UsageEvent.created_at >= period_start
            )
        )
        tokens_res = await db.execute(tokens_stmt)
        current_tokens = tokens_res.scalar() or 0

        # 4. Enforce limits using Boundary Rule: current + requested <= limit
        # Check API calls limit (requesting 1 call)
        if current_api_calls + 1 > plan.max_api_calls:
            raise QuotaExceededException(
                message=f"Usage quota exceeded. Monthly limit is {plan.max_api_calls:,} API calls, current usage is {current_api_calls:,} API calls, requested 1 API call."
            )

        # Check Token limit (if tokens are requested)
        if requested_tokens > 0 and (current_tokens + requested_tokens > plan.max_tokens):
            raise QuotaExceededException(
                message=f"Usage quota exceeded. Monthly limit is {plan.max_tokens:,} AI tokens, current usage is {current_tokens:,} AI tokens, requested {requested_tokens:,} tokens."
            )
