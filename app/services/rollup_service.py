import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.usage_event import UsageEvent

class RollupService:
    @staticmethod
    async def get_usage_rollup(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        """
        Calculates aggregate usage data and cost for a tenant within their current billing cycle.
        """
        # 1. Fetch Subscription to find billing period start date
        sub_stmt = select(Subscription).filter_by(tenant_id=tenant_id)
        sub_res = await db.execute(sub_stmt)
        subscription = sub_res.scalar_one_or_none()
        
        if not subscription:
            plan_id = "free"
            status = "active"
            period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            plan_id = subscription.plan_id
            status = subscription.status
            period_start = subscription.current_period_start
            if not period_start:
                period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
        # 2. Count API calls (type='api_call' quantity + count of type='ai_token' events)
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
 
        total_api_calls = api_calls_sum + ai_tokens_count
        
        # 3. Sum token metrics and cost since period_start
        tokens_stmt = (
            select(
                func.sum(UsageEvent.token_input).label("input"),
                func.sum(UsageEvent.token_cached_input).label("cached"),
                func.sum(UsageEvent.token_output).label("output"),
                func.sum(UsageEvent.token_reasoning).label("reasoning"),
                func.sum(UsageEvent.cost_microcents).label("cost")
            )
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.type == "ai_token",
                UsageEvent.created_at >= period_start
            )
        )
        tokens_res = await db.execute(tokens_stmt)
        row = tokens_res.first()
        
        input_tokens = 0
        cached_tokens = 0
        output_tokens = 0
        reasoning_tokens = 0
        total_cost_microcents = 0
        
        if row and row.cost is not None:
            input_tokens = row.input or 0
            cached_tokens = row.cached or 0
            output_tokens = row.output or 0
            reasoning_tokens = row.reasoning or 0
            total_cost_microcents = row.cost or 0
            
        return {
            "tenant_id": str(tenant_id),
            "plan_id": plan_id,
            "status": status,
            "usage": {
                "api_calls": total_api_calls,
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_tokens,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "cost_microcents": total_cost_microcents
            }
        }
