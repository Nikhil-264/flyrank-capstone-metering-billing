# Phase 1 — Design (≈4–6h)

Gate to pass before Phase 2 starts: design doc signed off (this file,
fully checked, plus `docs/architecture.md` and `docs/data-model.md`
filled in with real paths, not placeholders).

## Checklist
- [x] Database schema drafted: tenants, plans, subscriptions,
      usage_events, webhook_events (columns + types + constraints).
- [x] Plans + quotas defined and entered into `knowledge/pricing-plan.md`.
- [x] Metering API contract written: request/response shape for
      `POST /generate`, including idempotency key header/field.
- [x] Idempotency strategy decided and written into `rules/idempotency.md`
      if it differs from the default there (unique constraint + fast-path
      pre-check).
- [x] `docs/architecture.md` updated with real file paths (not "planned").
- [x] One explicit non-goal stated (per capstone Ground Rules: "Pick
      one, early... one explicit non-goal").
- [x] Repo created: public, named `flyrank-capstone-metering-billing`,
      first commit = README skeleton + `.gitignore`.

## Non-goal (fill in before starting Phase 2)
> Proration calculation on mid-cycle subscription downgrades, automatic PDF invoice generation, and email dispatch of invoices to users are non-goals for the core engine.


## Evidence
Paste proof of repo creation + first commit hash into `EVIDENCE.md`
under "Phase 1".
