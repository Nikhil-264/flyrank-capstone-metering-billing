import asyncio
import json
import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config.settings import settings
from app.models.webhook_event import WebhookEvent
from app.services.stripe_helpers import get_period_dates, meta_get
from app.services.subscription_sync import SubscriptionSync

router = APIRouter()
logger = logging.getLogger("app.webhooks.stripe")

stripe.api_key = settings.STRIPE_SECRET_KEY

_HANDLED = {
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


def _duplicate_response():
    return {"status": "success", "message": "duplicate"}


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify signature against the raw body BEFORE parsing, deduplicate by Stripe
    event id, then mirror the tenant's plan/status. Payment truth lives at
    Stripe; this endpoint only ever applies verified events.
    """
    payload_bytes = await request.body()

    # 1. Signature verification (before touching the payload).
    try:
        event = stripe.Webhook.construct_event(
            payload_bytes, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(
            status_code=400, detail=f"Webhook signature verification failed: {str(e)}"
        )

    # 2. Event-id deduplication (fast path).
    if await db.get(WebhookEvent, event.id):
        return _duplicate_response()

    db.add(
        WebhookEvent(
            id=event.id,
            type=event.type,
            payload=json.loads(payload_bytes.decode("utf-8")),
        )
    )

    # 3. Apply supported events.
    if event.type == "checkout.session.completed":
        await _handle_checkout_completed(db, event)
    elif event.type in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_event(db, event)
    else:
        logger.info("stripe webhook: ignoring unhandled event type %s", event.type)

    # 4. Commit both the WebhookEvent row and any subscription changes atomically.
    #    A concurrent duplicate delivery loses the unique-id race here -> treat
    #    as an already-processed duplicate (same discipline as MeterService).
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return _duplicate_response()

    return {"status": "success", "message": "event processed"}


async def _resolve_tenant_id(db, obj) -> uuid.UUID | None:
    tenant_id_str = meta_get(obj.metadata, "tenant_id")
    if tenant_id_str:
        try:
            return uuid.UUID(tenant_id_str)
        except ValueError:
            logger.warning("stripe webhook: invalid tenant_id metadata %r", tenant_id_str)
            return None
    sub_id = getattr(obj, "id", None)
    if sub_id:
        return await SubscriptionSync.get_tenant_id_by_stripe_sub_id(db, sub_id)
    return None


async def _handle_checkout_completed(db, event):
    session = event.data.object
    tenant_id_str = meta_get(session.metadata, "tenant_id")
    if not tenant_id_str:
        logger.warning("stripe webhook: checkout.session.completed without tenant_id metadata")
        return
    tenant_id = uuid.UUID(tenant_id_str)

    stripe_sub_id = session.subscription
    if not stripe_sub_id:
        logger.warning(
            "stripe webhook: checkout.session.completed for tenant %s has no subscription",
            tenant_id,
        )
        return

    stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
    start_dt, end_dt = get_period_dates(stripe_sub)
    await SubscriptionSync.sync_subscription(
        db=db,
        tenant_id=tenant_id,
        stripe_sub_id=stripe_sub_id,
        stripe_cus_id=session.customer,
        plan_id=meta_get(stripe_sub.metadata, "plan_id", "pro"),
        status=stripe_sub.status,
        current_period_start=start_dt,
        current_period_end=end_dt,
    )


async def _handle_subscription_event(db, event):
    sub = event.data.object
    tenant_id = await _resolve_tenant_id(db, sub)
    if tenant_id is None:
        logger.warning(
            "stripe webhook: %s could not be matched to a local tenant (sub %s)",
            event.type,
            getattr(sub, "id", "?"),
        )
        return

    if event.type == "customer.subscription.deleted":
        await SubscriptionSync.cancel_subscription(db, tenant_id)
        return

    start_dt, end_dt = get_period_dates(sub)
    await SubscriptionSync.sync_subscription(
        db=db,
        tenant_id=tenant_id,
        stripe_sub_id=sub.id,
        stripe_cus_id=sub.customer,
        plan_id=meta_get(sub.metadata, "plan_id", "pro"),
        status=sub.status,
        current_period_start=start_dt,
        current_period_end=end_dt,
    )
