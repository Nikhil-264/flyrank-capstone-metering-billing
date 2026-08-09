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
- [ ] README + architecture diagram + setup instructions; submission-pack
      files present (`README.md`, `capstone.yaml`, `EVIDENCE.md`,
      `BUILDLOG.md`, `.env.example`).

## Exit condition
This file is "done" when zero unticked boxes remain above AND all five
probes in `docs/evaluation-probes.md` pass against a running instance.
