# Architecture — Pointer Map

Doc Truth standard: this file never describes *how* code behaves in
prose — it points to the file that behaves that way. The code is truth;
this is the map. If a path below doesn't exist yet, it's planned, not
built — check `SPECS.md` for status.

## Request flow (one metering path, one read path, one payment-sync path, one job path)
```
Client ─► POST /generate (billable action)  → app/api/generate.py
  ├─ duplicate idempotency key? → return original result (no new event)
  ├─► app/services/quota_service.py :: check_quota()   [BEFORE persisting]
  │     ├─ locks the subscription row FOR UPDATE (serializes concurrent callers)
  │     ├─ no / inactive subscription → 402  (app/api/errors.py)
  │     └─ limit exceeded            → 429 + Retry-After
  └─► app/services/meter_service.py :: MeterService.record()
        ├─ app/services/cost_service.py :: price()  (config in app/config/pricing.py)
        └─ store usage_event → app/models/usage_event.py
              (uq_tenant_idempotency_key backstops the pre-check under races)

Usage numbers ("used so far this period") come from ONE place —
app/services/usage_query.py — shared by quota enforcement and the rollup.

GET /usage → app/api/usage.py → app/services/rollup_service.py

Stripe Checkout (test mode) → app/api/checkout.py → app/services/stripe_service.py
Stripe webhook ─► app/api/webhooks/stripe.py
  ├─ verify signature against the raw body FIRST (bad → 400)
  ├─ dedupe by event id → app/models/webhook_event.py
  │    (concurrent duplicate delivery: unique-id IntegrityError → treated as dup)
  └─ sync tenant plan/status → app/services/subscription_sync.py
       (Stripe helpers shared with the job: app/services/stripe_helpers.py)

Nightly (APScheduler, app/jobs/scheduler.py)
  └─► app/jobs/runner.py :: run_job()  (≤3 retries, job_runs record, CRITICAL alert)
        └─► app/services/reconciliation_service.py  (pull Stripe truth, repair drift)
  Manual trigger / inspection: app/api/admin_jobs.py  (POST /admin/jobs/reconcile, GET /admin/jobs)
```

## Layers
| Layer | Path | Owns |
|---|---|---|
| HTTP | `app/api/` | Request parsing, status codes, no business logic |
| Service/logic | `app/services/` | Metering, quota, pricing, usage aggregation, Stripe sync, reconciliation |
| Jobs | `app/jobs/` | Scheduler + generic retry/alert job runner |
| Data | `app/models/`, `app/db/` | SQLAlchemy models, migrations |
| Config | `app/config/` | Settings + pinned pricing constants |

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
> **429 responses carry a `Retry-After` header** — integer seconds until the
> quota window resets (`current_period_end`, else the first instant of next
> calendar month). Machine callers should honour it.

> [!NOTE]
> **Tenant Provisioning Requirement:** An active subscription row (defaulting to the `free` plan) must be provisioned in the database alongside any newly created Tenant. This database relationship ensures that subsequent calls to `POST /generate` do not fail with a 402/404 subscription status check. `GET /usage` for a tenant with **no** subscription row reports `plan_id: "none"`, `status: "none"` (it does not pretend the tenant is on an active free plan) — consistent with the 402 `/generate` would return.

### `POST /admin/jobs/reconcile` and `GET /admin/jobs`
On-demand trigger and history for the background reconciliation job. No
authorization (same scope caveat as the rest of the service). `reconcile`
runs the sweep synchronously and records a `job_runs` row; the retry/alert
wrapper lives in the *scheduled* path (`app/jobs/runner.py`).

### Billable-call accounting (why `type='api_call'` rows are rare)
`POST /generate` writes exactly **one** `usage_event` per call
(`type='ai_token'`). That single row counts as *1 API call* against the
API-call quota and *N tokens* against the token quota — see
`app/services/usage_query.py`. Standalone `type='api_call'` rows are still
supported (bulk/administrative metering) and are covered by
`tests/test_metering.py`; the single billable endpoint just doesn't emit them.

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

