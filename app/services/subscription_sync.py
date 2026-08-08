import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import Subscription

class SubscriptionSync:
    @staticmethod
    async def sync_subscription(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        stripe_sub_id: str,
        stripe_cus_id: str,
        plan_id: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Subscription:
        """
        Sync a subscription received from a Stripe webhook with the local database.
        Updates fields if the subscription already exists for the tenant, or creates a new one.
        """
        stmt = select(Subscription).filter_by(tenant_id=tenant_id)
        res = await db.execute(stmt)
        subscription = res.scalar_one_or_none()
        
        if subscription:
            subscription.stripe_subscription_id = stripe_sub_id
            subscription.stripe_customer_id = stripe_cus_id
            subscription.plan_id = plan_id
            subscription.status = status
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
        else:
            subscription = Subscription(
                tenant_id=tenant_id,
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=stripe_cus_id,
                plan_id=plan_id,
                status=status,
                current_period_start=current_period_start,
                current_period_end=current_period_end
            )
            db.add(subscription)
            
        await db.flush()
        return subscription

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        tenant_id: uuid.UUID
    ) -> Subscription:
        """
        Downgrade the tenant to the free plan upon subscription deletion/cancellation on Stripe.
        """
        stmt = select(Subscription).filter_by(tenant_id=tenant_id)
        res = await db.execute(stmt)
        subscription = res.scalar_one_or_none()
        
        if subscription:
            subscription.plan_id = "free"
            subscription.status = "active"
            subscription.stripe_subscription_id = None
            # Keep stripe_customer_id intact so they are linked
            await db.flush()
            
        return subscription

    @staticmethod
    async def get_tenant_id_by_stripe_sub_id(
        db: AsyncSession,
        stripe_sub_id: str
    ) -> Optional[uuid.UUID]:
        """
        Look up the local tenant ID associated with a Stripe subscription ID.
        Used as a fallback if metadata is missing.
        """
        stmt = select(Subscription.tenant_id).filter_by(stripe_subscription_id=stripe_sub_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
