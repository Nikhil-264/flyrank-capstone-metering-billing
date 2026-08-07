# Data Model — Pointer Map

Truth lives in the migrations, not here. This is the index.

| Entity | Model file (planned) | Migration (planned) | Notes |
|---|---|---|---|
| tenant | `app/models/tenant.py` | `alembic/versions/0001_*.py` | Root of isolation — every other table FKs to it |
| plan | `app/models/plan.py` | same | Free / Pro, seeded not user-created |
| subscription | `app/models/subscription.py` | same | Mirrors Stripe subscription state |
| usage_event | `app/models/usage_event.py` | same | Unique constraint on (tenant_id, idempotency_key) — see `rules/idempotency.md` |
| webhook_event | `app/models/webhook_event.py` | same | Stripe event_id unique constraint for dedup |

## Isolation rule
Every query that touches `usage_event`, `subscription`, or any
tenant-owned row must be scoped by `tenant_id` at the query layer, not
just filtered after fetch. Reviewed as part of the "Security" rubric
dimension.
