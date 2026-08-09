# reconcile_stripe.py
import asyncio
import uuid
from datetime import datetime, timezone
import stripe
from sqlalchemy import select
from app.config.settings import settings
from app.db.session import async_session_maker
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.services.subscription_sync import SubscriptionSync

stripe.api_key = settings.STRIPE_SECRET_KEY

def _meta_get(metadata, key, default=None):
    if metadata is None:
        return default
    if isinstance(metadata, dict):
        return metadata.get(key, default)
    return getattr(metadata, key, default)

def _get_period_dates(sub):
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

async def main(db_session=None):
    print("=== STARTING STRIPE SUBSCRIPTION RECONCILIATION JOB ===")
    
    # 1. Fetch all active/trialing/past_due/canceled subscriptions from Stripe
    # (Checking limit 100 for test mode purposes)
    try:
        stripe_subs = await asyncio.to_thread(
            stripe.Subscription.list,
            limit=100,
            status="all"
        )
    except Exception as e:
        print(f"Error fetching subscriptions from Stripe: {e}")
        return

    print(f"Fetched {len(stripe_subs.data)} subscriptions from Stripe.")

    if db_session:
        await _reconcile(db_session, stripe_subs.data)
    else:
        async with async_session_maker() as db:
            await _reconcile(db, stripe_subs.data)
            await db.commit()

async def _reconcile(db, stripe_subs_data):
    # Keep track of active stripe subscription IDs
    active_stripe_sub_ids = set()
    
    # 2. Iterate and sync subscriptions that exist in Stripe
    for sub in stripe_subs_data:
        # We only care about active/trialing subscriptions to update
        if sub.status in ("active", "trialing"):
            tenant_id_str = _meta_get(sub.metadata, "tenant_id")
            
            # If tenant_id metadata is missing on the sub, try to look up locally
            tenant_id = None
            if tenant_id_str:
                try:
                    tenant_id = uuid.UUID(tenant_id_str)
                except ValueError:
                    print(f"Invalid UUID in metadata for subscription {sub.id}: {tenant_id_str}")
            else:
                tenant_id = await SubscriptionSync.get_tenant_id_by_stripe_sub_id(db, sub.id)
            
            if tenant_id:
                # Check if tenant exists in the database
                tenant_stmt = select(Tenant).filter_by(id=tenant_id)
                tenant_res = await db.execute(tenant_stmt)
                tenant_obj = tenant_res.scalar_one_or_none()
                
                if not tenant_obj:
                    print(f"Tenant {tenant_id} not found in database. Skipping reconciliation for subscription {sub.id}.")
                    continue

                active_stripe_sub_ids.add(sub.id)
                plan_id = _meta_get(sub.metadata, "plan_id", "pro")
                status = sub.status
                start_ts, end_ts = _get_period_dates(sub)
                start_dt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
                
                # Check current DB state
                stmt = select(Subscription).filter_by(tenant_id=tenant_id)
                res = await db.execute(stmt)
                local_sub = res.scalar_one_or_none()
                
                # Check if update is needed
                needs_update = (
                    not local_sub or
                    local_sub.stripe_subscription_id != sub.id or
                    local_sub.plan_id != plan_id or
                    local_sub.status != status or
                    local_sub.current_period_end.replace(tzinfo=timezone.utc) != end_dt
                )
                
                if needs_update:
                    print(f"Syncing tenant {tenant_id}: plan={plan_id}, status={status}")
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
                else:
                    print(f"Tenant {tenant_id} is already in sync.")
    
    # 3. Identify and cancel any local subscriptions that were canceled/deleted on Stripe
    # but did not trigger/propagate via webhooks (active stripe ID set mismatch)
    stmt = select(Subscription).filter(
        Subscription.stripe_subscription_id.isnot(None)
    )
    res = await db.execute(stmt)
    local_subs = res.scalars().all()
    
    for local_sub in local_subs:
        # If the local sub points to a Stripe sub id that is no longer active in Stripe
        if local_sub.stripe_subscription_id not in active_stripe_sub_ids:
            # Double check the current status of that specific subscription in Stripe
            try:
                stripe_sub_detail = await asyncio.to_thread(
                    stripe.Subscription.retrieve,
                    local_sub.stripe_subscription_id
                )
                sub_status = stripe_sub_detail.status
            except stripe.error.InvalidRequestError:
                # Subscription doesn't exist on Stripe
                sub_status = "canceled"
            except Exception as e:
                print(f"Error checking subscription {local_sub.stripe_subscription_id}: {e}")
                continue
            
            if sub_status in ("canceled", "incomplete_expired"):
                print(f"Canceled Stripe subscription detected locally for tenant {local_sub.tenant_id}. Canceling local sub.")
                await SubscriptionSync.cancel_subscription(db, local_sub.tenant_id)
    
    print("=== STRIPE SUBSCRIPTION RECONCILIATION JOB COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(main())
