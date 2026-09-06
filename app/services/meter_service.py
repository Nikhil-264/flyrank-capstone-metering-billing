import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage_event import UsageEvent
from app.services.cost_service import CostService
from app.api.errors import InvalidUsageError

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

        # 2. Validate quantity > 0
        if quantity <= 0:
            raise InvalidUsageError("Usage quantity must be greater than zero.")

        # 3. Calculate cost in micro-cents using CostService
        cost_microcents = CostService.price(
            type=type,
            quantity=quantity,
            token_input=token_input,
            token_cached_input=token_cached_input,
            token_output=token_output,
            token_reasoning=token_reasoning
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
