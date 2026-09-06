# SPECS.md — Master Definition of Done

Living checklist. Read chronologically, execute by shared importance
(anchors let you jump to a phase's own `tasks/<phase>/SPECS.md` for
implementation-level detail). Tick a box here only when the matching
phase-level spec is fully checked AND evidence is pasted in `EVIDENCE.md`.

## Metering
- [x] ⚓ A billable action creates exactly one usage event, even under
      retries — deduplicated by idempotency key. → `tasks/phase-2-core-billing/SPECS.md`
- [x] A test proves double-counting cannot happen.

## Quotas
- [x] ⚓ Usage is checked against the tenant's plan; over-limit requests
      are rejected. → `tasks/phase-2-core-billing/SPECS.md`
- [x] Responses carry correct status codes (429 / 402) and an explanatory
      message.

## Cost calculation
- [x] ⚓ Monthly usage rolls up into a cost figure per tenant. → `tasks/phase-4-cost-hardening/SPECS.md`
- [x] AI token pricing handles cached input, reasoning tokens, and output
      pricing correctly (see `knowledge/pricing-plan.md`).
- [x] Pricing constants are pinned in config and covered by tests.

## Stripe integration
- [x] ⚓ Subscription checkout works end-to-end in Stripe test mode. → `tasks/phase-3-stripe-integration/SPECS.md`
- [x] Webhooks verify signatures, ignore duplicate events, and update
      tenant plan/status.

## Data model, tests & documentation
- [x] Database includes tenants, plans, subscriptions, usage_events;
      tenant data isolated.
- [x] Tests cover: duplicate usage prevention, quota boundaries (at /
      just-under / over), cost calculations, invalid-webhook rejection,
      duplicate-webhook handling.
- [x] README + architecture diagram + setup instructions; submission-pack
      files present (`README.md`, `capstone.yaml`, `EVIDENCE.md`,
      `BUILDLOG.md`, `.env.example`).

## Shared requirements (capstone §12 — the eight cross-cutting patterns)
- [x] Layered architecture — `app/api` / `app/services` / `app/models` (+ `app/jobs`)
- [x] Validation at the boundary — bad input → typed 4xx envelope, never a 500
      (`app/api/errors.py`; blanket `ValueError` catch removed in favour of
      `InvalidUsageError` + a `RequestValidationError` handler)
- [x] ≥1 background job — nightly Stripe reconciliation via APScheduler,
      with retries + a durable `job_runs` record + a CRITICAL failure alert
      (`app/jobs/`), on-demand trigger at `POST /admin/jobs/reconcile`
- [x] Real persistence — Alembic migrations `0001`+`0002`; lookup index
      `ix_usage_events_tenant_type_created`; tenant-scoped queries
- [x] Idempotency where it matters — `/generate` (constraint-backed) and
      Stripe webhooks (event-id PK, concurrent-insert safe)
- [x] Secrets clean — env only, `.env` git-ignored, not logged
- [x] Cost tracked — per event, attributed to tenant, priced from pinned
      config (AI is simulated, so no live budget guard needed)
- [x] Tests that matter — dedupe, quota boundary + race, pinned pricing,
      invalid/duplicate webhook, tenant isolation, job retry/alert

## Exit condition
This file is "done" when zero unticked boxes remain above AND all five
probes in `docs/evaluation-probes.md` pass against a running instance.
