# Data Model — Pointer Map

Truth lives in the migrations, not here. This is the index.

| Entity | Model file | Migration | Notes |
|---|---|---|---|
| tenant | `app/models/tenant.py` | `alembic/versions/0001_initial_tables.py` | Root of isolation — every other table FKs to it |
| plan | `app/models/plan.py` | `0001` | Free / Pro, seeded not user-created |
| subscription | `app/models/subscription.py` | `0001` | Mirrors Stripe subscription state; `current_period_*` nullable (NULL → calendar-month fallback) |
| usage_event | `app/models/usage_event.py` | `0001` + `0002` | Unique `(tenant_id, idempotency_key)` (see `rules/idempotency.md`); lookup index `(tenant_id, type, created_at)` in `0002` |
| webhook_event | `app/models/webhook_event.py` | `0001` | Stripe `event_id` is the PK — dedup by primary key |
| job_run | `app/models/job_run.py` | `0002` | One row per background-job execution: `running`/`success`/`failed`, attempts, error text |

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
- `cost_microcents`: `BIGINT` (Not Null) — integer micro-cents (1e-6 USD); never float
- `created_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- **Constraints**: Unique `(tenant_id, idempotency_key)` (`uq_tenant_idempotency_key`)
- **Indexes**: `(tenant_id, type, created_at)` (`ix_usage_events_tenant_type_created`) —
  every quota check and rollup filters on exactly these columns
  (`app/services/usage_query.py`)

**Billable-call accounting:** `POST /generate` writes one `ai_token` row per
call; it counts as 1 API call *and* N tokens. `api_call`-typed rows are for
bulk/administrative metering and add their `quantity` to the API-call total.

### webhook_events
- `id`: `VARCHAR(255)` (Primary Key, Stripe Event ID `evt_...`) — dedup is by PK
- `type`: `VARCHAR(255)` (Not Null)
- `processed_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- `payload`: `JSONB` (Not Null)

### job_runs
- `id`: `UUID` (Primary Key)
- `job_name`: `VARCHAR(100)` (Not Null, e.g. `'stripe_reconciliation'`)
- `status`: `VARCHAR(20)` (Not Null, `'running'` | `'success'` | `'failed'`)
- `attempts`: `INTEGER` (Not Null, default `0`)
- `started_at`: `TIMESTAMP WITH TIME ZONE` (Not Null, default `now()`)
- `finished_at`: `TIMESTAMP WITH TIME ZONE` (Nullable)
- `error`: `TEXT` (Nullable — traceback when `status='failed'`)
- **Indexes**: `(job_name, started_at)` (`ix_job_runs_job_name_started`)

## Isolation rule
Every query that touches `usage_event`, `subscription`, or any
tenant-owned row must be scoped by `tenant_id` at the query layer, not
just filtered after fetch. Reviewed as part of the "Security" rubric
dimension.

