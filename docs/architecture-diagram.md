# Architecture Diagram

Kept in sync with `docs/architecture.md`'s flow — update both together.

```mermaid
flowchart TD
    Client -->|POST /generate + Idempotency-Key| API[FastAPI: app/api]
    API --> Dedup{Idempotency-Key seen?}
    Dedup -->|yes| Return[Return original result — no new event]
    Dedup -->|no| Quota[QuotaService.check_quota — locks subscription FOR UPDATE]
    Quota -->|no / inactive subscription| Err402[402 Payment Required]
    Quota -->|limit exceeded| Err429[429 + Retry-After]
    Quota -->|allowed| Meter[MeterService.record + CostService.price]
    Meter --> Store[(usage_event)]
    Store --> Resp[200 response]

    ClientC[Client] -->|POST /checkout| Checkout[app/api/checkout.py]
    Checkout --> Stripe[(Stripe Test Mode)]
    Stripe -->|signed webhook| WH[app/api/webhooks/stripe.py]
    WH --> Verify[Verify signature FIRST]
    Verify -->|bad sig| Err400[400 — nothing changes]
    Verify -->|dup event id| NoOp[No-op, 2xx]
    Verify -->|ok, new event| Sync[subscription_sync.py]
    Sync --> DB[(tenant / subscription)]

    ClientR[Client] -->|GET /usage| Rollup[rollup_service.py]
    Rollup --> DB

    Cron[APScheduler — nightly 03:00 UTC] --> Runner[run_job: retries + job_runs + CRITICAL alert]
    Runner --> Recon[reconciliation_service — Stripe is source of truth]
    Recon --> DB
```

Quota check happens **before** the usage event is written (a rejected request
never persists a row). `usage_query.py` is the single source of the "used so
far this period" numbers for both `QuotaService` and `RollupService`.

Paste a rendered PNG/SVG export of this into the README once the app
exists, if the grader's viewer doesn't render Mermaid inline.
