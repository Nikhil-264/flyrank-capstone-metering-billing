import logging
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
logger = logging.getLogger("app.api.checkout")


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    x_tenant_id: uuid.UUID = Header(..., alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout Session to upgrade a tenant to Pro.
    """
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == x_tenant_id))
    ).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    subscription = (
        await db.execute(
            select(Subscription).where(Subscription.tenant_id == x_tenant_id)
        )
    ).scalar_one_or_none()
    stripe_customer_id = subscription.stripe_customer_id if subscription else None

    success_url = "http://localhost:8000/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = "http://localhost:8000/cancel"

    try:
        session = await StripeService.create_checkout_session(
            tenant_id=x_tenant_id,
            success_url=success_url,
            cancel_url=cancel_url,
            stripe_customer_id=stripe_customer_id,
        )
    except Exception as e:  # noqa: BLE001
        # Log the detail server-side; do not leak Stripe internals to the caller.
        logger.error("Stripe checkout session creation failed for tenant %s: %s", x_tenant_id, e)
        raise HTTPException(
            status_code=502, detail="Unable to create a checkout session right now."
        )

    return CheckoutResponse(session_id=session.id, checkout_url=session.url)
