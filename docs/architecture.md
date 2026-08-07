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

## Diagram
A rendered version of the flow above (for the README) lives at
`docs/architecture-diagram.md` — keep both in sync when the flow
changes.
