import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.usage_event import UsageEvent

async def create_tenant_with_subscription(
    db: AsyncSession,
    name: str,
    plan_id: str = "free",
    status: str = "active"
) -> tuple[Tenant, Subscription]:
    """Helper to set up a tenant and a subscription in the test database."""
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    subscription = Subscription(
        tenant_id=tenant.id,
        plan_id=plan_id,
        status=status,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc)
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return tenant, subscription

@pytest.mark.asyncio
async def test_generate_endpoint_requires_headers(client: AsyncClient):
    """Verify that generate endpoint requires X-Tenant-ID and Idempotency-Key headers."""
    # Missing both headers
    response = await client.post("/generate", json={"prompt": "hello"})
    assert response.status_code == 422

    # Missing X-Tenant-ID
    response = await client.post(
        "/generate",
        headers={"Idempotency-Key": "key-1"},
        json={"prompt": "hello"}
    )
    assert response.status_code == 422

    # Missing Idempotency-Key
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(uuid.uuid4())},
        json={"prompt": "hello"}
    )
    assert response.status_code == 422

    # Invalid UUID for Tenant ID
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": "not-a-uuid", "Idempotency-Key": "key-1"},
        json={"prompt": "hello"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_generate_endpoint_payment_required(db: AsyncSession, client: AsyncClient):
    """Verify 402 error is returned if tenant's subscription is inactive/canceled."""
    tenant, sub = await create_tenant_with_subscription(db, "Canceled Tenant", status="canceled")

    response = await client.post(
        "/generate",
        headers={
            "X-Tenant-ID": str(tenant.id),
            "Idempotency-Key": "key-1"
        },
        json={
            "prompt": "Write a song.",
            "mock_usage": {"input_tokens": 10}
        }
    )
    
    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "Payment Required"
    assert data["code"] == "PAYMENT_REQUIRED"
    assert "Active subscription required. Plan is currently 'canceled'" in data["message"]

@pytest.mark.asyncio
async def test_generate_endpoint_token_quota_boundary(db: AsyncSession, client: AsyncClient):
    """
    Verify boundary checks for token quota:
    - Under limit (99,900 / 100,000): Allowed
    - At limit (100,000 / 100,000): Allowed
    - Over limit (100,001 / 100,000): Rejected with 429
    """
    tenant, sub = await create_tenant_with_subscription(db, "Token Tenant", plan_id="free")

    # 1. Drive usage near the limit (use 99,900 tokens)
    # Free plan limit is 100,000 AI tokens
    event1 = UsageEvent(
        tenant_id=tenant.id,
        type="ai_token",
        quantity=99900,
        idempotency_key="fill-key-1",
        token_input=99900,
        cost_microcents=99900 * 10
    )
    db.add(event1)
    await db.commit()

    # 2. Request 100 tokens (this brings total exactly to 100,000 / 100,000 limit)
    # This must be allowed by boundary rule (current_usage + requested_usage <= limit)
    response = await client.post(
        "/generate",
        headers={
            "X-Tenant-ID": str(tenant.id),
            "Idempotency-Key": "exactly-at-limit-key"
        },
        json={
            "prompt": "Test limit",
            "mock_usage": {
                "input_tokens": 100  # Brings total to 100,000
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["usage"]["input_tokens"] == 100

    # 3. Request 1 token (brings total to 100,001 / 100,000 limit)
    # This must be rejected with 429
    response = await client.post(
        "/generate",
        headers={
            "X-Tenant-ID": str(tenant.id),
            "Idempotency-Key": "over-limit-key"
        },
        json={
            "prompt": "Test over limit",
            "mock_usage": {
                "input_tokens": 1
            }
        }
    )
    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "Quota Exceeded"
    assert data["code"] == "QUOTA_EXCEEDED"
    assert "Usage quota exceeded. Monthly limit is 100,000 AI tokens, current usage is 100,000 AI tokens, requested 1 tokens." in data["message"]

@pytest.mark.asyncio
async def test_generate_endpoint_api_call_quota_boundary(db: AsyncSession, client: AsyncClient):
    """
    Verify boundary checks for API call quota:
    - Free plan has a limit of 1,000 API calls.
    - 999 existing API calls: Request #1000 should be allowed.
    - 1,000 existing API calls: Request #1001 should return 429.
    """
    tenant, sub = await create_tenant_with_subscription(db, "Call Tenant", plan_id="free")

    # 1. Drive usage near limit by writing 999 api_call events
    for i in range(999):
        event = UsageEvent(
            tenant_id=tenant.id,
            type="api_call",
            quantity=1,
            idempotency_key=f"api-fill-{i}",
            cost_microcents=0
        )
        db.add(event)
    await db.commit()

    # 2. Request #1000 (brings current + requested API calls to 1,000 / 1,000 limit)
    # This must be allowed by boundary rule
    response = await client.post(
        "/generate",
        headers={
            "X-Tenant-ID": str(tenant.id),
            "Idempotency-Key": "at-call-limit-key"
        },
        json={"prompt": "Request #1000"}
    )
    assert response.status_code == 200

    # 3. Request #1001 (brings total API calls to 1,001 / 1,000 limit)
    # This must be rejected with 429
    response = await client.post(
        "/generate",
        headers={
            "X-Tenant-ID": str(tenant.id),
            "Idempotency-Key": "over-call-limit-key"
        },
        json={"prompt": "Request #1001"}
    )
    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "Quota Exceeded"
    assert data["code"] == "QUOTA_EXCEEDED"
    assert "Usage quota exceeded. Monthly limit is 1,000 API calls, current usage is 1,000 API calls, requested 1 API call." in data["message"]
