# Data Model — Pointer Map

Truth lives in the migrations, not here. This is the index.

| Entity | Model file (planned) | Migration (planned) | Notes |
|---|---|---|---|
| tenant | `app/models/tenant.py` | `alembic/versions/0001_*.py` | Root of isolation — every other table FKs to it |
| plan | `app/models/plan.py` | same | Free / Pro, seeded not user-created |
| subscription | `app/models/subscription.py` | same | Mirrors Stripe subscription state |
| usage_event | `app/models/usage_event.py` | same | Unique constraint on (tenant_id, idempotency_key) — see `rules/idempotency.md` |
| webhook_event | `app/models/webhook_event.py` | same | Stripe event_id unique constraint for dedup |

## Detailed Schema Draft

### tenants
- `id`: `UUID` (Primary Key)
- `name`: `VARCHAR(255)` (Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)

### plans
- `id`: `VARCHAR(50)` (Primary Key, e.g. `'free'`, `'pro'`)
- `name`: `VARCHAR(255)` (Not Null)
- `max_api_calls`: `INTEGER` (Not Null)
- `max_tokens`: `INTEGER` (Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)

### subscriptions
- `id`: `UUID` (Primary Key)
- `tenant_id`: `UUID` (Foreign Key -> `tenants.id`, Unique, Not Null)
- `stripe_subscription_id`: `VARCHAR(255)` (Unique, Nullable)
- `stripe_customer_id`: `VARCHAR(255)` (Nullable)
- `plan_id`: `VARCHAR(50)` (Foreign Key -> `plans.id`, Not Null)
- `status`: `VARCHAR(50)` (Not Null, e.g., `'active'`, `'canceled'`, `'incomplete'`)
- `current_period_start`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `current_period_end`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- `updated_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)

### usage_events
- `id`: `UUID` (Primary Key)
- `tenant_id`: `UUID` (Foreign Key -> `tenants.id`, Not Null)
- `type`: `VARCHAR(50)` (Not Null, `'api_call'` or `'ai_token'`)
- `quantity`: `INTEGER` (Not Null)
- `idempotency_key`: `VARCHAR(255)` (Not Null)
- `token_input`: `INTEGER` (Nullable)
- `token_cached_input`: `INTEGER` (Nullable)
- `token_output`: `INTEGER` (Nullable)
- `token_reasoning`: `INTEGER` (Nullable)
- `cost_microcents`: `BIGINT` (Not Null)
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- **Constraints**: Unique index on `(tenant_id, idempotency_key)`

### webhook_events
- `id`: `VARCHAR(255)` (Primary Key, Stripe Event ID `evt_...`)
- `type`: `VARCHAR(255)` (Not Null)
- `processed_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- `payload`: `JSONB` (Not Null)

## Isolation rule
Every query that touches `usage_event`, `subscription`, or any
tenant-owned row must be scoped by `tenant_id` at the query layer, not
just filtered after fetch. Reviewed as part of the "Security" rubric
dimension.

