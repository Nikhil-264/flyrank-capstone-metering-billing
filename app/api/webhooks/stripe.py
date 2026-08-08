import json
import uuid
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config.settings import settings
from app.models.webhook_event import WebhookEvent
from app.services.subscription_sync import SubscriptionSync

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY


def _meta_get(metadata, key, default=None):
    """
    Read a key from Stripe metadata regardless of whether it's a real
    stripe.StripeObject (parsed from a webhook payload -- attribute-style
    access only, no .get()) or a plain dict (as used by mocked
    stripe.Subscription.retrieve in tests). Never call .get() directly
    on a StripeObject -- see learnings.md.
    """
    if metadata is None:
        return default
    if isinstance(metadata, dict):
        return metadata.get(key, default)
    return getattr(metadata, key, default)


def _get_period_dates(sub):
    """
    Safely extract current_period_start and current_period_end timestamps
    from a Stripe subscription object.
    Supports legacy top-level attributes and 2025-03-31.basil+ (Dahlia)
    nested items structure for both real StripeObjects and mock dictionaries.
    """
    start = getattr(sub, "current_period_start", None) or (sub.get("current_period_start") if isinstance(sub, dict) or hasattr(sub, "get") else None)
    end = getattr(sub, "current_period_end", None) or (sub.get("current_period_end") if isinstance(sub, dict) or hasattr(sub, "get") else None)
    
    if start is None:
        items = getattr(sub, "items", None) or (sub.get("items") if isinstance(sub, dict) or hasattr(sub, "get") else None)
        if items:
            data = getattr(items, "data", None) or (items.get("data") if isinstance(items, dict) or hasattr(items, "get") else None)
            if data and len(data) > 0:
                item = data[0]
                start = getattr(item, "current_period_start", None) or (item.get("current_period_start") if isinstance(item, dict) or hasattr(item, "get") else None)
                end = getattr(item, "current_period_end", None) or (item.get("current_period_end") if isinstance(item, dict) or hasattr(item, "get") else None)
                
    if start is None:
        import time
        start = int(time.time())
        end = start + 30 * 24 * 60 * 60
        
    return start, end

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Stripe Webhook Handler.
    Verifies signature before touching payload, deduplicates events by Stripe Event ID,
    and updates tenant subscription state in the database based on webhook events.
    """
    payload_bytes = await request.body()
    
    # 1. Signature verification before touching the payload
    try:
        event = stripe.Webhook.construct_event(
            payload_bytes,
            stripe_signature,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")
        
    # 2. Event-ID deduplication
    existing_event = await db.get(WebhookEvent, event.id)
    if existing_event:
        # Replayed event -> processed once; subsequent delivery returns 200 OK
        return {"status": "success", "message": "duplicate"}
        
    # Record webhook event to avoid reprocessing
    webhook_event = WebhookEvent(
        id=event.id,
        type=event.type,
        payload=json.loads(payload_bytes.decode('utf-8'))
    )
    db.add(webhook_event)
    
    # 3. Process supported events
    if event.type == "checkout.session.completed":
        session = event.data.object
        tenant_id_str = _meta_get(session.metadata, "tenant_id")
        
        if tenant_id_str:
            tenant_id = uuid.UUID(tenant_id_str)
            stripe_sub_id = session.subscription
            stripe_cus_id = session.customer
            
            if stripe_sub_id:
                # Fetch subscription from Stripe to get period dates and status
                import asyncio
                stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
                
                plan_id = _meta_get(stripe_sub.metadata, "plan_id", "pro")
                status = stripe_sub.status
                start_ts, end_ts = _get_period_dates(stripe_sub)
                start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
                
                await SubscriptionSync.sync_subscription(
                    db=db,
                    tenant_id=tenant_id,
                    stripe_sub_id=stripe_sub_id,
                    stripe_cus_id=stripe_cus_id,
                    plan_id=plan_id,
                    status=status,
                    current_period_start=start_dt,
                    current_period_end=end_dt
                )
                
    elif event.type == "customer.subscription.updated":
        sub = event.data.object
        tenant_id_str = _meta_get(sub.metadata, "tenant_id")
        tenant_id = None
        
        if tenant_id_str:
            tenant_id = uuid.UUID(tenant_id_str)
        else:
            tenant_id = await SubscriptionSync.get_tenant_id_by_stripe_sub_id(db, sub.id)
            
        if tenant_id:
            plan_id = _meta_get(sub.metadata, "plan_id", "pro")
            status = sub.status
            start_ts, end_ts = _get_period_dates(sub)
            start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
            
            await SubscriptionSync.sync_subscription(
                db=db,
                tenant_id=tenant_id,
                stripe_sub_id=sub.id,
                stripe_cus_id=sub.customer,
                plan_id=plan_id,
                status=status,
                current_period_start=start_dt,
                current_period_end=end_dt
            )
            
    elif event.type == "customer.subscription.deleted":
        sub = event.data.object
        tenant_id_str = _meta_get(sub.metadata, "tenant_id")
        tenant_id = None
        
        if tenant_id_str:
            tenant_id = uuid.UUID(tenant_id_str)
        else:
            tenant_id = await SubscriptionSync.get_tenant_id_by_stripe_sub_id(db, sub.id)
            
        if tenant_id:
            await SubscriptionSync.cancel_subscription(db, tenant_id)
            
    # Commit transaction to persist both webhook event insertion and subscription updates
    await db.commit()
    
    return {"status": "success", "message": "event processed"}
