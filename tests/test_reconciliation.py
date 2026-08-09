# tests/test_reconciliation.py
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import stripe

from app.models.tenant import Tenant
from app.models.subscription import Subscription
from reconcile_stripe import main as run_reconciliation

async def create_test_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

@pytest.mark.asyncio
@patch("stripe.Subscription.list")
async def test_reconciliation_syncs_pro_subscription(
    mock_sub_list,
    db: AsyncSession
):
    """
    Verify that when Stripe has an active subscription but the local DB is out of sync,
    running reconciliation updates the local DB to match Stripe.
    """
    tenant = await create_test_tenant(db, "Reconciliation Sync Tenant")
    
    # 1. Provision a local Free active subscription
    sub = Subscription(
        tenant_id=tenant.id,
        stripe_subscription_id=None,
        stripe_customer_id=None,
        plan_id="free",
        status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc)
    )
    db.add(sub)
    await db.commit()
    
    # 2. Mock Stripe returns one active Pro subscription for this tenant
    mock_stripe_sub = MagicMock()
    mock_stripe_sub.id = "sub_reconcile_123"
    mock_stripe_sub.customer = "cus_reconcile_123"
    mock_stripe_sub.status = "active"
    mock_stripe_sub.current_period_start = 1770000000
    mock_stripe_sub.current_period_end = 1780000000
    mock_stripe_sub.metadata = {"tenant_id": str(tenant.id), "plan_id": "pro"}
    
    mock_sub_list.return_value = MagicMock(data=[mock_stripe_sub])
    
    # 3. Run reconciliation
    await run_reconciliation(db)
    
    # 4. Check DB results
    tenant_id = tenant.id
    db.expire_all()
    stmt = select(Subscription).filter_by(tenant_id=tenant_id)
    res = await db.execute(stmt)
    updated_sub = res.scalar_one_or_none()
    
    assert updated_sub is not None
    assert updated_sub.plan_id == "pro"
    assert updated_sub.status == "active"
    assert updated_sub.stripe_subscription_id == "sub_reconcile_123"
    assert updated_sub.stripe_customer_id == "cus_reconcile_123"

@pytest.mark.asyncio
@patch("stripe.Subscription.retrieve")
@patch("stripe.Subscription.list")
async def test_reconciliation_downgrades_canceled_subscription(
    mock_sub_list,
    mock_sub_retrieve,
    db: AsyncSession
):
    """
    Verify that when local DB has a Stripe subscription but Stripe indicates it is canceled
    (missing from list and confirmed canceled via retrieve), reconciliation downgrades the tenant to Free.
    """
    tenant = await create_test_tenant(db, "Reconciliation Downgrade Tenant")
    
    # 1. Provision local active Pro subscription pointing to stripe
    sub = Subscription(
        tenant_id=tenant.id,
        stripe_subscription_id="sub_canceled_999",
        stripe_customer_id="cus_canceled_999",
        plan_id="pro",
        status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc)
    )
    db.add(sub)
    await db.commit()
    
    # 2. Stripe list returns empty (no active subscriptions)
    mock_sub_list.return_value = MagicMock(data=[])
    
    # 3. Stripe retrieve returns a canceled status
    mock_canceled_sub = MagicMock()
    mock_canceled_sub.status = "canceled"
    mock_sub_retrieve.return_value = mock_canceled_sub
    
    # 4. Run reconciliation
    await run_reconciliation(db)
    
    # 5. Check DB results
    tenant_id = tenant.id
    db.expire_all()
    stmt = select(Subscription).filter_by(tenant_id=tenant_id)
    res = await db.execute(stmt)
    downgraded_sub = res.scalar_one_or_none()
    
    assert downgraded_sub is not None
    assert downgraded_sub.plan_id == "free"
    assert downgraded_sub.status == "active"
    assert downgraded_sub.stripe_subscription_id is None
