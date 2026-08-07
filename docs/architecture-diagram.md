# Architecture Diagram

Kept in sync with `docs/architecture.md`'s flow — update both together.

```mermaid
flowchart TD
    Client -->|POST /generate + idempotency key| API[FastAPI: app/api]
    API --> Meter[MeterService.record]
    Meter -->|duplicate key| Return[Return original result]
    Meter -->|new key| Store[(usage_event)]
    Store --> Quota[QuotaService.check]
    Quota -->|allowed| Cost[CostService.price]
    Quota -->|exceeded| Err[402 / 429]
    Cost --> Resp[200 response]

    ClientC[Client] -->|Checkout| Checkout[app/api/checkout.py]
    Checkout --> Stripe[(Stripe Test Mode)]
    Stripe -->|webhook| WH[app/api/webhooks/stripe.py]
    WH --> Verify[Verify signature]
    Verify -->|bad sig| Err400[400]
    Verify -->|ok, new event| Sync[subscription_sync.py]
    Verify -->|ok, dup event id| NoOp[No-op, 2xx]
    Sync --> DB[(tenant / subscription)]

    ClientR[Client] -->|GET /usage| Rollup[rollup_service.py]
    Rollup --> DB
```

Paste a rendered PNG/SVG export of this into the README once the app
exists, if the grader's viewer doesn't render Mermaid inline.
