import uuid
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.rollup_service import RollupService

router = APIRouter()

class RollupUsage(BaseModel):
    api_calls: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_microcents: int

class UsageResponse(BaseModel):
    tenant_id: str
    plan_id: str
    status: str
    usage: RollupUsage

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    x_tenant_id: uuid.UUID = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the subscription plan, status, and usage rollup for the tenant.
    """
    # 1. Verify tenant exists
    tenant_stmt = select(Tenant).filter_by(id=x_tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # 2. Get rollup from RollupService
    usage_data = await RollupService.get_usage_rollup(db, x_tenant_id)
    return usage_data
