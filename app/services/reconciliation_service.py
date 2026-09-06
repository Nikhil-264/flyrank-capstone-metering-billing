"""
Stripe subscription reconciliation.

A defensive sweep that makes the local database match Stripe's view, catching
subscription changes that never arrived via webhook (missed/deferred events,
downtime). Stripe is the source of billing truth; this job only ever pulls
from Stripe, never pushes.

Called two ways:
  * on a schedule  -> app/jobs/scheduler.py  (nightly, with retries + alert)
  * on demand      -> POST /admin/jobs/reconcile  and  reconcile_stripe.py CLI
"""
import asyncio
import logging
import uuid
from datetime import timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.services.stripe_helpers import get_period_dates, meta_get
from app.services.subscription_sync import SubscriptionSync

logger = logging.getLogger("app.reconciliation")

# Canonical job name (shared by the scheduler and the admin trigger).
RECONCILIATION_JOB_NAME = "stripe_reconciliation"

stripe.api_key = settings.STRIPE_SECRET_KEY

_ACTIVE = ("active", "trialing")
_DEAD = ("canceled", "incomplete_expired")


async def reconcile(db: AsyncSession, stripe_subs_data) -> dict:
    """
    Apply Stripe's subscription list to the local DB. Returns a summary dict
    (also useful as the job result). Does not commit — the caller owns the
    transaction boundary.
    """
    synced = 0
    already_in_sync = 0
    downgraded = 0
    skipped = 0
    active_stripe_sub_ids: set[str] = set()

    for sub in stripe_subs_data:
        if sub.status not in _ACTIVE:
            continue

        tenant_id_str = meta_get(sub.metadata, "tenant_id")
        tenant_id: uuid.UUID | None = None
        if tenant_id_str:
            try:
                tenant_id = uuid.UUID(tenant_id_str)
            except ValueError:
                logger.warning(
                    "reconcile: invalid tenant_id metadata %r on subscription %s",
                    tenant_id_str,
                    sub.id,
                )
        else:
            tenant_id = await SubscriptionSync.get_tenant_id_by_stripe_sub_id(db, sub.id)

        if tenant_id is None:
            logger.warning(
                "reconcile: could not resolve a local tenant for Stripe subscription %s",
                sub.id,
            )
            skipped += 1
            continue

        tenant_obj = (
            await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalar_one_or_none()
        if tenant_obj is None:
            logger.warning(
                "reconcile: tenant %s (subscription %s) not in database; skipping",
                tenant_id,
                sub.id,
            )
            skipped += 1
            continue

        active_stripe_sub_ids.add(sub.id)
        plan_id = meta_get(sub.metadata, "plan_id", "pro")
        start_dt, end_dt = get_period_dates(sub)

        local_sub = (
            await db.execute(
                select(Subscription).where(Subscription.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

        local_end = None
        if local_sub and local_sub.current_period_end:
            local_end = local_sub.current_period_end
            if local_end.tzinfo is None:
                local_end = local_end.replace(tzinfo=timezone.utc)

        needs_update = (
            local_sub is None
            or local_sub.stripe_subscription_id != sub.id
            or local_sub.plan_id != plan_id
            or local_sub.status != sub.status
            or local_end != end_dt
        )

        if needs_update:
            logger.info(
                "reconcile: syncing tenant %s -> plan=%s status=%s", tenant_id, plan_id, sub.status
            )
            await SubscriptionSync.sync_subscription(
                db=db,
                tenant_id=tenant_id,
                stripe_sub_id=sub.id,
                stripe_cus_id=sub.customer,
                plan_id=plan_id,
                status=sub.status,
                current_period_start=start_dt,
                current_period_end=end_dt,
            )
            synced += 1
        else:
            already_in_sync += 1

    # Local subscriptions that point at a Stripe sub no longer active -> confirm
    # and downgrade (catches a missed customer.subscription.deleted).
    linked_local = (
        await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id.isnot(None))
        )
    ).scalars().all()

    for local_sub in linked_local:
        if local_sub.stripe_subscription_id in active_stripe_sub_ids:
            continue
        try:
            detail = await asyncio.to_thread(
                stripe.Subscription.retrieve, local_sub.stripe_subscription_id
            )
            sub_status = detail.status
        except stripe.error.InvalidRequestError:
            sub_status = "canceled"
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "reconcile: could not retrieve subscription %s: %s",
                local_sub.stripe_subscription_id,
                e,
            )
            continue

        if sub_status in _DEAD:
            logger.info(
                "reconcile: Stripe subscription for tenant %s is %s; downgrading to free",
                local_sub.tenant_id,
                sub_status,
            )
            await SubscriptionSync.cancel_subscription(db, local_sub.tenant_id)
            downgraded += 1

    summary = {
        "fetched": len(stripe_subs_data),
        "synced": synced,
        "already_in_sync": already_in_sync,
        "downgraded": downgraded,
        "skipped": skipped,
    }
    logger.info("reconcile: %s", summary)
    return summary


async def reconcile_from_stripe(db: AsyncSession) -> dict:
    """Fetch every subscription from Stripe, then reconcile. Caller commits."""
    stripe_subs = await asyncio.to_thread(
        stripe.Subscription.list, limit=100, status="all"
    )
    return await reconcile(db, stripe_subs.data)
