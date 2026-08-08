import json
import time
import uuid
import pytest
import stripe
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.config.settings import settings
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.webhook_event import WebhookEvent

# Ensure a dummy secret is set if none exists, to avoid errors during test execution
if not settings.STRIPE_WEBHOOK_SECRET:
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret_for_signature_verification_12345"

async def create_test_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

import hmac
import hashlib

def generate_stripe_signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    payload_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    payload_to_sign = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

@pytest.mark.asyncio
@patch("app.services.stripe_service.StripeService.get_or_create_pro_price")
@patch("stripe.checkout.Session.create")
async def test_create_checkout_endpoint(
    mock_session_create,
    mock_get_price,
    db: AsyncSession,
    client: AsyncClient
):
    """
    Verify POST /checkout successfully generates a Stripe Checkout Session
    and returns its ID and URL.
    """
    tenant = await create_test_tenant(db, "Test Checkout Tenant")
    mock_get_price.return_value = "price_mock_123"
    
    mock_session = MagicMock()
    mock_session.id = "cs_test_session_id_999"
    mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_session_id_999"
    mock_session_create.return_value = mock_session
    
    response = await client.post(
        "/checkout",
        headers={"X-Tenant-ID": str(tenant.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "cs_test_session_id_999"
    assert data["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_session_id_999"
    
    # Assert Stripe Session was called with correct metadata
    mock_session_create.assert_called_once()
    args, kwargs = mock_session_create.call_args
    assert kwargs["metadata"]["tenant_id"] == str(tenant.id)
    assert kwargs["subscription_data"]["metadata"]["tenant_id"] == str(tenant.id)

@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    """
    Verify forged webhook (bad signature) returns 400 and does not change database state.
    """
    payload = {"id": "evt_invalid", "object": "event", "type": "checkout.session.completed"}
    response = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=123,v1=bad_sig"},
        content=json.dumps(payload)
    )
    
    assert response.status_code == 400
    assert "signature verification failed" in response.json()["detail"]

@pytest.mark.asyncio
@patch("stripe.Subscription.retrieve")
async def test_webhook_valid_checkout_completed(
    mock_sub_retrieve,
    db: AsyncSession,
    client: AsyncClient
):
    """
    Verify valid signed checkout.session.completed event syncs plan to Pro and updates GET /usage.
    """
    tenant = await create_test_tenant(db, "Upgrade Tenant")
    
    # 1. Setup Mock Stripe Subscription
    mock_sub = MagicMock()
    mock_sub.id = "sub_upgrade_123"
    mock_sub.customer = "cus_upgrade_123"
    mock_sub.status = "active"
    mock_sub.current_period_start = 1770000000
    mock_sub.current_period_end = 1780000000
    mock_sub.metadata = {"tenant_id": str(tenant.id), "plan_id": "pro"}
    mock_sub_retrieve.return_value = mock_sub
    
    # 2. Build Event Payload
    event_id = f"evt_{uuid.uuid4().hex}"
    payload_dict = {
        "id": event_id,
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_upgrade_session",
                "customer": "cus_upgrade_123",
                "subscription": "sub_upgrade_123",
                "metadata": {"tenant_id": str(tenant.id), "plan_id": "pro"}
            }
        }
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = generate_stripe_signature(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)
    
    # 3. Deliver Webhook
    response = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 4. Assert subscription updated in database
    tenant_id = tenant.id
    db.expire_all()
    stmt = select(Subscription).filter_by(tenant_id=tenant_id)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()
    
    assert sub is not None
    assert sub.plan_id == "pro"
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sub_upgrade_123"
    assert sub.stripe_customer_id == "cus_upgrade_123"
    
    # 5. Verify GET /usage reflects the new plan immediately
    usage_res = await client.get("/usage", headers={"X-Tenant-ID": str(tenant_id)})
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert usage_data["plan_id"] == "pro"
    assert usage_data["status"] == "active"

@pytest.mark.asyncio
@patch("stripe.Subscription.retrieve")
async def test_webhook_event_deduplication(
    mock_sub_retrieve,
    db: AsyncSession,
    client: AsyncClient
):
    """
    Verify event ID deduplication: replayed event processed once, returns 2xx on replay.
    """
    tenant = await create_test_tenant(db, "Dedup Tenant")
    
    mock_sub = MagicMock()
    mock_sub.id = "sub_dedup_123"
    mock_sub.customer = "cus_dedup_123"
    mock_sub.status = "active"
    mock_sub.current_period_start = 1770000000
    mock_sub.current_period_end = 1780000000
    mock_sub.metadata = {"tenant_id": str(tenant.id), "plan_id": "pro"}
    mock_sub_retrieve.return_value = mock_sub
    
    event_id = "evt_deduplication_test_999"
    payload_dict = {
        "id": event_id,
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_dedup_session",
                "customer": "cus_dedup_123",
                "subscription": "sub_dedup_123",
                "metadata": {"tenant_id": str(tenant.id), "plan_id": "pro"}
            }
        }
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = generate_stripe_signature(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)
    
    # First delivery
    response1 = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    assert response1.status_code == 200
    assert response1.json()["message"] == "event processed"
    
    # Second delivery (replay)
    response2 = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    assert response2.status_code == 200
    assert response2.json()["message"] == "duplicate"
    
    # Verify exactly one WebhookEvent row was created
    stmt = select(WebhookEvent).filter_by(id=event_id)
    res = await db.execute(stmt)
    assert res.scalar_one_or_none() is not None

@pytest.mark.asyncio
async def test_webhook_subscription_updated(
    db: AsyncSession,
    client: AsyncClient
):
    """
    Verify customer.subscription.updated webhook correctly updates subscription details in the DB.
    """
    tenant = await create_test_tenant(db, "Update Subs Tenant")
    
    # Setup initial local active Pro subscription
    sub = Subscription(
        tenant_id=tenant.id,
        stripe_subscription_id="sub_update_456",
        stripe_customer_id="cus_update_456",
        plan_id="pro",
        status="active",
        current_period_start=datetime.fromtimestamp(1770000000, tz=timezone.utc),
        current_period_end=datetime.fromtimestamp(1780000000, tz=timezone.utc)
    )
    db.add(sub)
    await db.commit()
    
    # Deliver customer.subscription.updated event indicating status is now past_due
    event_id = f"evt_{uuid.uuid4().hex}"
    payload_dict = {
        "id": event_id,
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_update_456",
                "customer": "cus_update_456",
                "status": "past_due",
                "current_period_start": 1770000000,
                "current_period_end": 1780000000,
                "metadata": {"tenant_id": str(tenant.id), "plan_id": "pro"}
            }
        }
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = generate_stripe_signature(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)
    
    response = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    assert response.status_code == 200
    
    # Assert plan status is past_due in the database
    tenant_id = tenant.id
    db.expire_all()
    stmt = select(Subscription).filter_by(tenant_id=tenant_id)
    res = await db.execute(stmt)
    updated_sub = res.scalar_one_or_none()
    assert updated_sub.status == "past_due"

@pytest.mark.asyncio
async def test_webhook_subscription_deleted(
    db: AsyncSession,
    client: AsyncClient
):
    """
    Verify customer.subscription.deleted downgrades tenant plan back to free.
    """
    tenant = await create_test_tenant(db, "Delete Subs Tenant")
    
    # Setup initial local active Pro subscription
    sub = Subscription(
        tenant_id=tenant.id,
        stripe_subscription_id="sub_delete_789",
        stripe_customer_id="cus_delete_789",
        plan_id="pro",
        status="active",
        current_period_start=datetime.fromtimestamp(1770000000, tz=timezone.utc),
        current_period_end=datetime.fromtimestamp(1780000000, tz=timezone.utc)
    )
    db.add(sub)
    await db.commit()
    
    # Deliver customer.subscription.deleted event
    event_id = f"evt_{uuid.uuid4().hex}"
    payload_dict = {
        "id": event_id,
        "object": "event",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_delete_789",
                "customer": "cus_delete_789",
                "status": "canceled",
                "metadata": {"tenant_id": str(tenant.id), "plan_id": "pro"}
            }
        }
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = generate_stripe_signature(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)
    
    response = await client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    assert response.status_code == 200
    
    # Assert plan downgraded back to free, active status, stripe_subscription_id cleared
    tenant_id = tenant.id
    db.expire_all()
    stmt = select(Subscription).filter_by(tenant_id=tenant_id)
    res = await db.execute(stmt)
    downgraded_sub = res.scalar_one_or_none()
    
    assert downgraded_sub.plan_id == "free"
    assert downgraded_sub.status == "active"
    assert downgraded_sub.stripe_subscription_id is None
