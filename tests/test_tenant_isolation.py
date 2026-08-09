import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.usage_event import UsageEvent
from app.services.meter_service import MeterService

async def create_tenant_with_subscription(
    db: AsyncSession,
    name: str,
    plan_id: str = "free",
    status: str = "active"
) -> tuple[Tenant, Subscription]:
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
async def test_tenant_isolation_usage_rollup(db: AsyncSession, client: AsyncClient):
    # Setup Tenant A and Tenant B
    tenant_a, sub_a = await create_tenant_with_subscription(db, "Tenant A")
    tenant_b, sub_b = await create_tenant_with_subscription(db, "Tenant B")

    # Record some usage for Tenant A
    await MeterService.record(
        db=db,
        tenant_id=tenant_a.id,
        type="ai_token",
        quantity=1000,
        idempotency_key="key-a-1",
        token_input=1000
    )
    await db.commit()

    # Rollup for Tenant A should have the usage
    response_a = await client.get("/usage", headers={"X-Tenant-ID": str(tenant_a.id)})
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert data_a["usage"]["input_tokens"] == 1000
    assert data_a["usage"]["cost_microcents"] == 10000

    # Rollup for Tenant B should remain completely isolated and empty (0s)
    response_b = await client.get("/usage", headers={"X-Tenant-ID": str(tenant_b.id)})
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert data_b["usage"]["input_tokens"] == 0
    assert data_b["usage"]["cost_microcents"] == 0

@pytest.mark.asyncio
async def test_endpoint_missing_tenant(client: AsyncClient):
    # Call generate with valid UUID not in database
    non_existent_id = str(uuid.uuid4())
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": non_existent_id, "Idempotency-Key": "key-test"},
        json={"prompt": "hello", "mock_usage": {"input_tokens": 100}}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"

    # Call usage with valid UUID not in database
    response = await client.get(
        "/usage",
        headers={"X-Tenant-ID": non_existent_id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"

    # Call checkout with valid UUID not in database
    response = await client.post(
        "/checkout",
        headers={"X-Tenant-ID": non_existent_id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"

@pytest.mark.asyncio
async def test_endpoint_malformed_idempotency_key(db: AsyncSession, client: AsyncClient):
    tenant, sub = await create_tenant_with_subscription(db, "Key Test Tenant")

    # Empty idempotency key
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(tenant.id), "Idempotency-Key": ""},
        json={"prompt": "hello"}
    )
    assert response.status_code == 400
    assert "Idempotency-Key header cannot be empty" in response.json()["detail"]

    # Whitespace idempotency key
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(tenant.id), "Idempotency-Key": "   "},
        json={"prompt": "hello"}
    )
    assert response.status_code == 400
    assert "Idempotency-Key header cannot be empty" in response.json()["detail"]

@pytest.mark.asyncio
async def test_endpoint_negative_or_zero_usage(db: AsyncSession, client: AsyncClient):
    tenant, sub = await create_tenant_with_subscription(db, "Qty Test Tenant")

    # Zero tokens requested
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(tenant.id), "Idempotency-Key": "zero-qty-key"},
        json={
            "prompt": "hello",
            "mock_usage": {
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0
            }
        }
    )
    assert response.status_code == 400
    assert "Requested token quantity must be greater than zero" in response.json()["detail"]

    # Omitted mock_usage (defaults to 1 token requested, which is allowed)
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(tenant.id), "Idempotency-Key": "omitted-qty-key"},
        json={"prompt": "hello"}
    )
    assert response.status_code == 200
    assert response.json()["usage"]["input_tokens"] == 1

    # Negative tokens requested (handled by Pydantic schema ge=0 validation)
    response = await client.post(
        "/generate",
        headers={"X-Tenant-ID": str(tenant.id), "Idempotency-Key": "neg-qty-key"},
        json={
            "prompt": "hello",
            "mock_usage": {
                "input_tokens": -5
            }
        }
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_meter_service_record_validates_quantity(db: AsyncSession):
    tenant = Tenant(name="Record Val Tenant")
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    with pytest.raises(ValueError, match="Usage quantity must be greater than zero"):
        await MeterService.record(
            db=db,
            tenant_id=tenant.id,
            type="ai_token",
            quantity=0,
            idempotency_key="zero-rec-key",
            token_input=0
        )
