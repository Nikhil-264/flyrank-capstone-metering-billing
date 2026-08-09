import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.services.meter_service import MeterService
from app.services.quota_service import QuotaService

router = APIRouter()

class MockUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = False
    mock_usage: Optional[MockUsage] = None

class UsageSummary(BaseModel):
    api_calls: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_microcents: int

class GenerateResponse(BaseModel):
    idempotency_key: str
    tenant_id: str
    text: str
    usage: UsageSummary

@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_tenant_id: uuid.UUID = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulated LLM generation endpoint.
    Checks subscription status and quota limits before recording usage.
    Deduplicates requests using Idempotency-Key.
    """
    # 1. Validate Idempotency-Key header (non-empty/non-whitespace)
    if not idempotency_key or idempotency_key.strip() == "":
        raise HTTPException(status_code=400, detail="Idempotency-Key header cannot be empty or whitespace.")

    # 2. Verify tenant exists in the database
    tenant_stmt = select(Tenant).filter_by(id=x_tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 3. Idempotency Check: check if key has already been processed and committed
    stmt = select(UsageEvent).filter_by(tenant_id=x_tenant_id, idempotency_key=idempotency_key)
    res = await db.execute(stmt)
    existing_event = res.scalar_one_or_none()

    if existing_event:
        # Return the original cached response
        return GenerateResponse(
            idempotency_key=existing_event.idempotency_key,
            tenant_id=str(existing_event.tenant_id),
            text="Simulated generation response.",
            usage=UsageSummary(
                api_calls=1,
                input_tokens=existing_event.token_input or 0,
                cached_input_tokens=existing_event.token_cached_input or 0,
                output_tokens=existing_event.token_output or 0,
                reasoning_tokens=existing_event.token_reasoning or 0,
                cost_microcents=existing_event.cost_microcents
            )
        )

    # 4. Parse token counts and validate they are positive
    if request.mock_usage:
        t_input = request.mock_usage.input_tokens
        t_cached = request.mock_usage.cached_input_tokens
        t_output = request.mock_usage.output_tokens
        t_reasoning = request.mock_usage.reasoning_tokens
        requested_tokens = t_input + t_cached + t_output + t_reasoning
        
        if requested_tokens <= 0:
            raise HTTPException(status_code=400, detail="Requested token quantity must be greater than zero.")
    else:
        # Default to 1 token if mock_usage is not provided to ensure a non-zero usage quantity
        t_input = 1
        t_cached = 0
        t_output = 0
        t_reasoning = 0
        requested_tokens = 1

    # 3. Quota check
    # Will raise 402 or 429 if the subscription is inactive or quota is exceeded
    await QuotaService.check_quota(db, x_tenant_id, requested_tokens)

    # 4. Record Usage Event
    # MeterService.record flushes the event to check database unique constraints
    event = await MeterService.record(
        db=db,
        tenant_id=x_tenant_id,
        type="ai_token",
        quantity=requested_tokens,
        idempotency_key=idempotency_key,
        token_input=t_input,
        token_cached_input=t_cached,
        token_output=t_output,
        token_reasoning=t_reasoning
    )

    # Commit the transaction to persist the event
    await db.commit()

    return GenerateResponse(
        idempotency_key=event.idempotency_key,
        tenant_id=str(event.tenant_id),
        text="Simulated generation response.",
        usage=UsageSummary(
            api_calls=1,
            input_tokens=event.token_input or 0,
            cached_input_tokens=event.token_cached_input or 0,
            output_tokens=event.token_output or 0,
            reasoning_tokens=event.token_reasoning or 0,
            cost_microcents=event.cost_microcents
        )
    )
