import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.services.stripe_service import StripeService

router = APIRouter()

class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    x_tenant_id: uuid.UUID = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a Stripe Checkout Session for upgrading a tenant to Pro.
    Returns the session ID and URL.
    """
    # 1. Verify tenant exists
    tenant_stmt = select(Tenant).filter_by(id=x_tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # 2. Check if there is an existing customer ID in subscriptions
    sub_stmt = select(Subscription).filter_by(tenant_id=x_tenant_id)
    sub_res = await db.execute(sub_stmt)
    subscription = sub_res.scalar_one_or_none()
    
    stripe_customer_id = subscription.stripe_customer_id if subscription else None
    
    # 3. Create Stripe Checkout Session
    # Redirect URLs can be success and cancel landing pages
    success_url = "http://localhost:8000/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = "http://localhost:8000/cancel"
    
    try:
        session = await StripeService.create_checkout_session(
            tenant_id=x_tenant_id,
            success_url=success_url,
            cancel_url=cancel_url,
            stripe_customer_id=stripe_customer_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe Checkout error: {str(e)}")
        
    return CheckoutResponse(
        session_id=session.id,
        checkout_url=session.url
    )
