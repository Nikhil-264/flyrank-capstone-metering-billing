# verify_probes.py
import sys
import uuid
import httpx
import hmac
import hashlib
import time
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.models.tenant import Tenant
from app.models.subscription import Subscription

API_URL = "http://api:8000"

def sign_payload(payload_bytes: bytes, secret: str) -> str:
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.".encode() + payload_bytes
    signature = hmac.new(
        secret.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def run_probes():
    print("=== STARTING LAYER 2 BEHAVIORAL PROBES ===")

    # 1. Setup a clean tenant for testing via direct DB connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def init_test_tenant():
        async with Session() as session:
            tenant = Tenant(name="Probe Test Tenant")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)

            sub = Subscription(
                tenant_id=tenant.id,
                plan_id="free",
                status="active",
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc)
            )
            session.add(sub)
            await session.commit()
            return tenant.id

    tenant_id = asyncio.run(init_test_tenant())
    print(f"Provisioned Probe Test Tenant: {tenant_id}")

    client = httpx.Client(base_url=API_URL)

    # ----------------------------------------------------
    # Probe 1: Idempotency probe
    # ----------------------------------------------------
    print("\n--- Running Probe 1: Idempotency ---")
    idempotency_key = f"probe-key-{uuid.uuid4()}"
    headers = {
        "X-Tenant-ID": str(tenant_id),
        "Idempotency-Key": idempotency_key
    }
    payload = {
        "prompt": "Probe test 1",
        "mock_usage": {
            "input_tokens": 100,
            "cached_input_tokens": 50,
            "output_tokens": 20,
            "reasoning_tokens": 10
        }
    }
    
    resp1 = client.post("/generate", headers=headers, json=payload)
    print(f"First request status: {resp1.status_code}")
    print(f"First response: {resp1.json()}")
    
    resp2 = client.post("/generate", headers=headers, json=payload)
    print(f"Second request status: {resp2.status_code}")
    print(f"Second response: {resp2.json()}")
    
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
    print("Probe 1 passed: Responses are identical, idempotency works.")

    # ----------------------------------------------------
    # Probe 2: Quota boundary probe
    # ----------------------------------------------------
    print("\n--- Running Probe 2: Quota Boundary ---")
    # Free plan token limit is 100,000.
    # The previous request used 100 + 50 + 20 + 10 = 180 tokens.
    # Let's request exactly 99,820 tokens to bring it exactly to 100,000.
    idempotency_key_boundary = f"probe-key-{uuid.uuid4()}"
    headers_boundary = {
        "X-Tenant-ID": str(tenant_id),
        "Idempotency-Key": idempotency_key_boundary
    }
    payload_boundary = {
        "prompt": "Boundary test",
        "mock_usage": {
            "input_tokens": 99820
        }
    }
    resp_boundary = client.post("/generate", headers=headers_boundary, json=payload_boundary)
    print(f"Boundary request status: {resp_boundary.status_code}")
    print(f"Boundary response: {resp_boundary.json()}")
    assert resp_boundary.status_code == 200

    # The next 1 token request should be blocked with 429
    idempotency_key_over = f"probe-key-{uuid.uuid4()}"
    headers_over = {
        "X-Tenant-ID": str(tenant_id),
        "Idempotency-Key": idempotency_key_over
    }
    payload_over = {
        "prompt": "Over limit test",
        "mock_usage": {
            "input_tokens": 1
        }
    }
    resp_over = client.post("/generate", headers=headers_over, json=payload_over)
    print(f"Over limit request status: {resp_over.status_code}")
    print(f"Over limit response: {resp_over.json()}")
    assert resp_over.status_code == 429
    assert resp_over.json()["code"] == "QUOTA_EXCEEDED"
    print("Probe 2 passed: Boundary request succeeded, subsequent request rejected with 429.")

    # ----------------------------------------------------
    # Probe 5: Pricing probe
    # ----------------------------------------------------
    print("\n--- Running Probe 5: Pricing Probe ---")
    # First request:
    # 100 input * 10 = 1,000
    # 50 cached * 2 = 100
    # 20 output * 30 = 600
    # 10 reasoning * 30 = 300
    # Total = 2,000 microcents
    #
    # Second request (boundary):
    # 99,820 input * 10 = 998,200 microcents
    # Total combined cost = 2,000 + 998,200 = 1,000,200 microcents.
    resp_usage = client.get("/usage", headers={"X-Tenant-ID": str(tenant_id)})
    print(f"Usage response status: {resp_usage.status_code}")
    print(f"Usage response: {resp_usage.json()}")
    
    assert resp_usage.status_code == 200
    usage_data = resp_usage.json()
    assert usage_data["usage"]["cost_microcents"] == 1000200
    print("Probe 5 passed: Total cost aggregates and matches expectations exactly.")

    # ----------------------------------------------------
    # Probe 3: Checkout probe
    # ----------------------------------------------------
    print("\n--- Running Probe 3: Checkout (Upgrade Webhook) ---")
    # Verify current plan is free
    assert usage_data["plan_id"] == "free"

    # Simulate Checkout session upgrade webhook (customer.subscription.updated)
    sub_id = f"sub_probe_{uuid.uuid4().hex[:12]}"
    cus_id = f"cus_probe_{uuid.uuid4().hex[:12]}"
    webhook_data = {
        "id": f"evt_probe_{uuid.uuid4().hex[:12]}",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": sub_id,
                "object": "subscription",
                "customer": cus_id,
                "status": "active",
                "current_period_start": int(time.time()),
                "current_period_end": int(time.time()) + 30*24*60*60,
                "metadata": {
                    "tenant_id": str(tenant_id),
                    "plan_id": "pro"
                }
            }
        }
    }
    import json
    payload_bytes = json.dumps(webhook_data).encode("utf-8")
    sig = sign_payload(payload_bytes, settings.STRIPE_WEBHOOK_SECRET)
    
    resp_webhook = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    print(f"Stripe Webhook status: {resp_webhook.status_code}")
    print(f"Stripe Webhook response: {resp_webhook.json()}")
    assert resp_webhook.status_code == 200

    # Query usage again to verify that plan is upgraded to pro immediately
    resp_usage_after = client.get("/usage", headers={"X-Tenant-ID": str(tenant_id)})
    print(f"Usage response after webhook: {resp_usage_after.json()}")
    assert resp_usage_after.json()["plan_id"] == "pro"
    print("Probe 3 passed: Webhook processed successfully, tenant plan upgraded to pro.")

    # ----------------------------------------------------
    # Probe 4: Webhook security probe
    # ----------------------------------------------------
    print("\n--- Running Probe 4: Webhook Security ---")
    # Forged signature -> 400
    resp_forged = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=123,v1=badsignature"},
        content=payload_bytes
    )
    print(f"Forged signature webhook status: {resp_forged.status_code}")
    assert resp_forged.status_code == 400

    # Duplicate delivery -> processed once (returns success duplicate)
    resp_replay = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": sig},
        content=payload_bytes
    )
    print(f"Replayed signature webhook status: {resp_replay.status_code}")
    print(f"Replayed signature webhook response: {resp_replay.json()}")
    assert resp_replay.status_code == 200
    assert resp_replay.json()["message"] == "duplicate"
    print("Probe 4 passed: Webhook signature verification and deduplication work perfectly.")

    print("\n=== ALL 5 LAYER 2 BEHAVIORAL PROBES COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_probes()
