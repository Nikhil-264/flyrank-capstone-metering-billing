# Phase 4 — Cost Calculation & Hardening (≈6–9h)

Gate to pass before Phase 5 starts: every pricing rule in
`knowledge/pricing-plan.md` has a pinned test matching a hand-computed
expected value; tenant isolation is proven, not assumed.

## Checklist
- [x] ⚓ `app/config/pricing.py` created: pinned constants for input,
      cached-input, output, and reasoning-as-output rates. No magic
      numbers elsewhere in the codebase.
- [x] `CostService.price()` implemented per `knowledge/pricing-plan.md`
      — categories priced separately, summed after pricing not before.
- [x] Worked example in `knowledge/pricing-plan.md` filled in with real
      numbers and mirrored by a pinned test.
- [x] `GET /usage` returns per-tenant rollup: usage by type + computed
      cost for the current period.
- [x] Tenant isolation test: tenant A cannot read or affect tenant B's
      usage/plan/subscription via any endpoint (try both direct ID
      guessing and missing-auth-header cases).
- [x] Error handling pass: malformed idempotency key, missing tenant,
      negative/zero usage quantities all rejected with clear 4xx, not
      500s.
- [x] Full test suite run clean end-to-end (`docker compose up` +
      test command from `README.md`), not just individual test files.

## Evidence
Paste the full pricing test output (all categories) and the tenant
isolation test result into `EVIDENCE.md` under "Phase 4".
