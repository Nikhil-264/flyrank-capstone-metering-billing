# EVIDENCE.md — Proof of Done

One entry per checked box, referencing the exact `SPECS.md` item it
proves. "Done" is observable — paste the actual test output / curl
transcript / log line, not a description of it.

## Format
```
### [Phase X] <checklist item text>
- Proof:
```
<paste test output / curl transcript / log line here>
```
```

## Phase 1 — Design

### [Phase 1] Repo created: public, named `flyrank-capstone-metering-billing`, first commit = README skeleton + `.gitignore`
- Proof: Repository initialized locally and pushed to GitHub with the initial harness scaffold.

### [Phase 1] Database schema drafted: tenants, plans, subscriptions, usage_events, webhook_events
- Proof: File [data-model.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/docs/data-model.md) contains explicit database column definitions, types, relationships, and unique constraints for all 5 entities.

### [Phase 1] Plans + quotas defined and entered into `knowledge/pricing-plan.md`
- Proof: File [pricing-plan.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/knowledge/pricing-plan.md) details exact monthly token and call quotas for Free and Pro plans, micro-cent rates for token categories (input, cached, output, thinking), and a worked pricing example.

### [Phase 1] Metering API contract written
- Proof: File [architecture.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/docs/architecture.md) documents HTTP headers, request body structure, 200 OK response payload, 429 Quota Exceeded payload, and 402 Payment Required payload for `POST /generate`.

### [Phase 1] Idempotency strategy decided and written
- Proof: Verified strategy in [idempotency.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/rules/idempotency.md) to use the unique constraint `(tenant_id, idempotency_key)` and fast-path database pre-checks.

### [Phase 1] One explicit non-goal stated
- Proof: Added explicit non-goals (invoicing and subscription downgrade proration bypasses) under the Non-goals section of [SPECS.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/tasks/phase-1-design/SPECS.md).



## Phase 2 — Core Billing

### [Phase 2] Metering & Idempotency Tests
- Proof: The automated pytest suite validates the `MeterService.record()` method and the endpoint quota limits. All 10 tests pass successfully (basic API calls, cost calculation, sequential deduplication, tenant-based scoping, concurrent race-condition handling, 402 subscription checks, and call/token quota boundary rules).
```
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 10 items

tests/test_metering.py ......                                                                       [ 60%]
tests/test_quota.py ....                                                                            [100%]

=========================================== 10 passed in 1.83s ============================================
```

## Phase 3 — Stripe Integration

### [Phase 3] Stripe test account connected; test Products/Prices created for Free/Pro
- Proof: Programmatic product "Pro Plan" lookup/creation with $49.00 USD monthly subscription price.
- Checkout session creation response:
```json
{
  "session_id": "cs_test_a14OmnBhscwXYv29HF69ODfiR46azNapj5JvKm0jb3hLmuLEtkHbcXNLUD",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_a14OmnBhscwXYv29HF69ODfiR46azNapj5JvKm0jb3hLmuLEtkHbcXNLUD"
}
```

### [Phase 3] Webhook signature verification, event-ID dedup, and tenant plan syncing
- Proof: Automated webhook tests verifying signature validation, 400 rejection for forged signatures, event-ID deduplication, and plan syncing:
```
tests/test_stripe_webhook.py ......                                                                 [100%]
=========================================== 16 passed in 2.77s ============================================
```

### [Phase 3] GET /usage reflects the new plan immediately after webhook processing
- Proof: Before and after `GET /usage` responses:
Before payment:
```json
{
  "tenant_id": "d721dfc3-c0ac-4250-b646-c03042a9995f",
  "plan_id": "free",
  "status": "active",
  "usage": {
    "api_calls": 0,
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "reasoning_tokens": 0,
    "cost_microcents": 0
  }
}
```

After payment completion and webhook delivery:
```json
{
  "tenant_id": "d721dfc3-c0ac-4250-b646-c03042a9995f",
  "plan_id": "pro",
  "status": "active",
  "usage": {
    "api_calls": 0,
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "reasoning_tokens": 0,
    "cost_microcents": 0
  }
}
```

## Phase 4 — Cost & Hardening

### [Phase 4] Pinned pricing constants & CostService pricing tests
- Proof: The automated tests in `tests/test_cost.py` validate the pricing model, ensuring that cached-input, reasoning-token, and standard rates produce the exact expected micro-cent values.
```
pytest tests/test_cost.py
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, asyncio-1.4.0
collected 4 items

tests/test_cost.py ....                                                 [100%]

============================== 4 passed in 0.08s ===============================
```

### [Phase 4] Tenant isolation and robust error handling
- Proof: The automated tests in `tests/test_tenant_isolation.py` verify that Tenant A cannot read or affect Tenant B's usage rollup, that missing or malformed headers return 4xx (422/400), and that zero/negative usage values are rejected properly.
```
pytest tests/test_tenant_isolation.py
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, asyncio-1.4.0
collected 5 items

tests/test_tenant_isolation.py .....                                    [100%]

============================== 5 passed in 0.32s ===============================
```

### [Phase 4] Full test suite execution
- Proof: The entire test suite ran successfully and passed cleanly.
```
PS C:\Users\HP\Documents\Coding journeys\FlyRank Internship Stuff\Capstones\flyrank-capstone-metering-billing> docker compose run --rm api pytest
[+] Creating 1/1
 ✔ Container billing-db  Running                                                 0.0s 
================================ test session starts =================================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 25 items

tests/test_cost.py ....                                                        [ 16%] 
tests/test_metering.py ......                                                  [ 40%]
tests/test_quota.py ....                                                       [ 56%]
tests/test_stripe_webhook.py ......                                            [ 80%]
tests/test_tenant_isolation.py .....                                           [100%]

================================= 25 passed in 3.55s ===============================
```

### [Phase 4] Layer-2 Behavioral Probes Verification
- Proof: The verification script `verify_probes.py` ran against the active docker composition and successfully validated all 5 behavioral probes.
```
=== STARTING LAYER 2 BEHAVIORAL PROBES ===
Provisioned Probe Test Tenant: 3d08e353-6111-445f-b11a-90fb9ed0408c

--- Running Probe 1: Idempotency ---
First request status: 200
First response: {'idempotency_key': 'probe-key-8c11b9ec-adf7-4ee0-b055-867667f495f7', 'tenant_id': '3d08e353-6111-445f-b11a-90fb9ed0408c', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 2000}}
Second request status: 200
Second response: {'idempotency_key': 'probe-key-8c11b9ec-adf7-4ee0-b055-867667f495f7', 'tenant_id': '3d08e353-6111-445f-b11a-90fb9ed0408c', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 2000}}
Probe 1 passed: Responses are identical, idempotency works.

--- Running Probe 2: Quota Boundary ---
Boundary request status: 200
Boundary response: {'idempotency_key': 'probe-key-b30a087a-9d8f-4720-bc20-1bf0abe24ec3', 'tenant_id': '3d08e353-6111-445f-b11a-90fb9ed0408c', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 99820, 'cached_input_tokens': 0, 'output_tokens': 0, 'reasoning_tokens': 0, 'cost_microcents': 998200}}
Over limit request status: 429
Over limit response: {'error': 'Quota Exceeded', 'message': 'Usage quota exceeded. Monthly limit is 100,000 AI tokens, current usage is 100,000 AI tokens, requested 1 tokens.', 'code': 'QUOTA_EXCEEDED'}
Probe 2 passed: Boundary request succeeded, subsequent request rejected with 429.     

--- Running Probe 5: Pricing Probe ---
Usage response status: 200
Usage response: {'tenant_id': '3d08e353-6111-445f-b11a-90fb9ed0408c', 'plan_id': 'free', 'status': 'active', 'usage': {'api_calls': 2, 'input_tokens': 99920, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 1000200}}
Probe 5 passed: Total cost aggregates and matches expectations exactly.

--- Running Probe 3: Checkout (Upgrade Webhook) ---
Stripe Webhook status: 200
Stripe Webhook response: {'status': 'success', 'message': 'event processed'}
Usage response after webhook: {'tenant_id': '3d08e353-6111-445f-b11a-90fb9ed0408c', 'plan_id': 'pro', 'status': 'active', 'usage': {'api_calls': 2, 'input_tokens': 99920, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 1000200}}
Probe 3 passed: Webhook processed successfully, tenant plan upgraded to pro.

--- Running Probe 4: Webhook Security ---
Forged signature webhook status: 400
Replayed signature webhook status: 200
Replayed signature webhook response: {'status': 'success', 'message': 'duplicate'}    
Probe 4 passed: Webhook signature verification and deduplication work perfectly.      

=== ALL 5 LAYER 2 BEHAVIORAL PROBES COMPLETED SUCCESSFULLY ===
```

## Phase 5 — Demo Prep

### [Phase 5] Run all five docs/evaluation-probes.md probes manually against a freshly-booted instance
- Proof: The verification script `verify_probes.py` was executed successfully against a clean, freshly-booted docker composition. Output transcript:
```
=== STARTING LAYER 2 BEHAVIORAL PROBES ===
Provisioned Probe Test Tenant: 4097c1dc-88a6-43d2-96e5-cf62abea75de

--- Running Probe 1: Idempotency ---
First request status: 200
First response: {'idempotency_key': 'probe-key-a0faf418-2b0b-4fd3-9e0f-0e519332dd25', 'tenant_id': '4097c1dc-88a6-43d2-96e5-cf62abea75de', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 2000}}
Second request status: 200
Second response: {'idempotency_key': 'probe-key-a0faf418-2b0b-4fd3-9e0f-0e519332dd25', 'tenant_id': '4097c1dc-88a6-43d2-96e5-cf62abea75de', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 2000}}
Probe 1 passed: Responses are identical, idempotency works.

--- Running Probe 2: Quota Boundary ---
Boundary request status: 200
Boundary response: {'idempotency_key': 'probe-key-2e24915e-6187-4ac8-9c3c-4244fbc8b096', 'tenant_id': '4097c1dc-88a6-43d2-96e5-cf62abea75de', 'text': 'Simulated generation response.', 'usage': {'api_calls': 1, 'input_tokens': 99820, 'cached_input_tokens': 0, 'output_tokens': 0, 'reasoning_tokens': 0, 'cost_microcents': 998200}}
Over limit request status: 429
Over limit response: {'error': 'Quota Exceeded', 'message': 'Usage quota exceeded. Monthly limit is 100,000 AI tokens, current usage is 100,000 AI tokens, requested 1 tokens.', 'code': 'QUOTA_EXCEEDED'}
Probe 2 passed: Boundary request succeeded, subsequent request rejected with 429.     

--- Running Probe 5: Pricing Probe ---
Usage response status: 200
Usage response: {'tenant_id': '4097c1dc-88a6-43d2-96e5-cf62abea75de', 'plan_id': 'free', 'status': 'active', 'usage': {'api_calls': 2, 'input_tokens': 99920, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 1000200}}
Probe 5 passed: Total cost aggregates and matches expectations exactly.

--- Running Probe 3: Checkout (Upgrade Webhook) ---
Stripe Webhook status: 200
Stripe Webhook response: {'status': 'success', 'message': 'event processed'}
Usage response after webhook: {'tenant_id': '4097c1dc-88a6-43d2-96e5-cf62abea75de', 'plan_id': 'pro', 'status': 'active', 'usage': {'api_calls': 2, 'input_tokens': 99920, 'cached_input_tokens': 50, 'output_tokens': 20, 'reasoning_tokens': 10, 'cost_microcents': 1000200}}
Probe 3 passed: Webhook processed successfully, tenant plan upgraded to pro.

--- Running Probe 4: Webhook Security ---
Forged signature webhook status: 400
Replayed signature webhook status: 200
Replayed signature webhook response: {'status': 'success', 'message': 'duplicate'}    
Probe 4 passed: Webhook signature verification and deduplication work perfectly.      

=== ALL 5 LAYER 2 BEHAVIORAL PROBES COMPLETED SUCCESSFULLY ===
```
