import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage_event import UsageEvent
from app.config.pricing import (
    INPUT_TOKEN_RATE,
    CACHED_INPUT_TOKEN_RATE,
    OUTPUT_TOKEN_RATE,
    REASONING_TOKEN_RATE,
    API_CALL_RATE
)

class MeterService:
    @staticmethod
    async def record(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        type: str,
        quantity: int,
        idempotency_key: str,
        token_input: Optional[int] = None,
        token_cached_input: Optional[int] = None,
        token_output: Optional[int] = None,
        token_reasoning: Optional[int] = None
    ) -> UsageEvent:
        """
        Record a usage event for a tenant.
        Ensures idempotency by checking (tenant_id, idempotency_key).
        If the key has been seen for this tenant, returns the original event.
        Otherwise, stores the event and flushes the database session to check constraints.
        """
        # 1. Fast-path pre-check
        stmt = select(UsageEvent).filter_by(tenant_id=tenant_id, idempotency_key=idempotency_key)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # 2. Calculate cost in micro-cents
        cost_microcents = 0
        if type == "api_call":
            cost_microcents = quantity * API_CALL_RATE
        elif type == "ai_token":
            t_input = token_input or 0
            t_cached = token_cached_input or 0
            t_output = token_output or 0
            t_reasoning = token_reasoning or 0
            
            cost_microcents = (
                (t_input * INPUT_TOKEN_RATE) +
                (t_cached * CACHED_INPUT_TOKEN_RATE) +
                (t_output * OUTPUT_TOKEN_RATE) +
                (t_reasoning * REASONING_TOKEN_RATE)
            )

        # 3. Create and add UsageEvent row
        event = UsageEvent(
            tenant_id=tenant_id,
            type=type,
            quantity=quantity,
            idempotency_key=idempotency_key,
            token_input=token_input,
            token_cached_input=token_cached_input,
            token_output=token_output,
            token_reasoning=token_reasoning,
            cost_microcents=cost_microcents
        )

        db.add(event)
        try:
            await db.flush()  # Flush to check database-level constraints
        except IntegrityError as e:
            await db.rollback()
            # Concurrency race condition: re-query database
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            # If not a unique constraint collision on the key, re-raise
            raise e
        
        return event
