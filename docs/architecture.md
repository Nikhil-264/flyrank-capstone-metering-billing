# Architecture — Pointer Map

Doc Truth standard: this file never describes *how* code behaves in
prose — it points to the file that behaves that way. The code is truth;
this is the map. If a path below doesn't exist yet, it's planned, not
built — check `SPECS.md` for status.

## Request flow (one metering path, one read path, one payment-sync path)
```
Client ─► POST /generate (billable action)
  └─► app/services/meter_service.py :: MeterService.record()
        ├─ duplicate idempotency key? → return original result
        ├─ store usage_event → app/models/usage_event.py
        └─► app/services/quota_service.py :: check()
              ├─ allowed → app/services/cost_service.py :: price()
              └─ exceeded → 402 / 429, app/api/errors.py

GET /usage → app/api/usage.py → app/services/rollup_service.py

Stripe Checkout (test mode) → app/api/checkout.py
Stripe webhook ─► app/api/webhooks/stripe.py
  ├─ verify signature → app/services/stripe_verify.py
  ├─ dedupe event → app/models/webhook_event.py
  └─ sync tenant plan/status → app/services/subscription_sync.py
```

## Layers
| Layer | Path | Owns |
|---|---|---|
| HTTP | `app/api/` | Request parsing, status codes, no business logic |
| Service/logic | `app/services/` | Metering, quota, pricing, Stripe sync |
| Data | `app/models/`, `app/db/` | SQLAlchemy models, migrations |
| Config | `app/config/pricing.py` | Pinned pricing constants |

## Swap test
Rubric dimension "Architecture" (capstone §12) asks: can you swap the
DB or a provider without touching business logic? If a service file
imports SQLAlchemy models directly instead of going through a
repository/interface, that's a flag — check `tech-debt-tracker.md`
before "fixing" it in case it's an intentional trade-off already logged.

## API Contracts

### `POST /generate`
- **Headers**:
  - `Idempotency-Key`: `string` (Required, unique request tracking)
  - `X-Tenant-ID`: `string` (Required, UUID identifying the tenant)
- **Request Body**:
  ```json
  {
    "prompt": "string",
    "stream": false,
    "mock_usage": {
      "input_tokens": 1000,
      "cached_input_tokens": 200,
      "output_tokens": 300,
      "reasoning_tokens": 50
    }
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "idempotency_key": "string",
    "tenant_id": "string",
    "text": "Simulated generation response.",
    "usage": {
      "api_calls": 1,
      "input_tokens": 1000,
      "cached_input_tokens": 200,
      "output_tokens": 300,
      "reasoning_tokens": 50,
      "cost_microcents": 209000
    }
  }
  ```
- **Response Body (429 Too Many Requests — Quota Exceeded)**:
  ```json
  {
    "error": "Quota Exceeded",
    "message": "Usage quota exceeded. Monthly limit is 100,000 AI tokens, current usage is 99,850 AI tokens, requested 350 tokens.",
    "code": "QUOTA_EXCEEDED"
  }
  ```
- **Response Body (402 Payment Required — Inactive/Canceled Subscription)**:
  ```json
  {
    "error": "Payment Required",
    "message": "Active subscription required. Plan is currently 'canceled'. Please upgrade or pay your outstanding invoice to resume.",
    "code": "PAYMENT_REQUIRED"
  }
  ```

> [!NOTE]
> **Tenant Provisioning Requirement:** An active subscription row (defaulting to the `free` plan) must be provisioned in the database alongside any newly created Tenant. This database relationship ensures that subsequent calls to `POST /generate` do not fail with a 402/404 subscription status check.

## Security scope (documented decision, not an oversight)
Tenant identity is entirely the `X-Tenant-ID` header value — there is
no auth token, API key, or session tying a caller to a tenant. Any
caller who knows (or guesses) a tenant's UUID can read that tenant's
`/usage` or act as them against `/generate` and `/checkout`.
`tests/test_tenant_isolation.py` proves data does not leak *between*
tenants when each is addressed by its own correct ID — it does not
prove a caller is who they claim to be. Real per-tenant authentication
(API keys or JWT-based auth) is out of core scope for this capstone
(see `tech-debt-tracker.md`'s scope-freeze entry) and would be the
first thing added if this went further than a capstone demo.

## Diagram
A rendered version of the flow above (for the README) lives at
`docs/architecture-diagram.md` — keep both in sync when the flow
changes.

