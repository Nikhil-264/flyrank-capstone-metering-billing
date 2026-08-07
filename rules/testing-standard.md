# Rule: Testing Standard ("Done" is Observable)

"Done" is never a feeling. Done means one of: a passing test, a curl
transcript, a specific API response, or (for UI-adjacent work, N/A on
this project) a Chrome DevTools verification — pasted into
`EVIDENCE.md` against the exact checkbox it proves.

## Minimum required coverage (maps to capstone §6 + §12 Probe list)
- Duplicate usage prevention (see `rules/idempotency.md`).
- Quota boundary cases: at limit, one under, one over
  (`rules/quota-and-status-codes.md`).
- Cost calculations: every pricing rule in `knowledge/pricing-plan.md`
  gets a hand-computed pinned test.
- Invalid webhook rejection + duplicate webhook handling
  (`rules/stripe-webhooks.md`).
- Tenant data isolation: tenant A can never read/affect tenant B's
  usage, plan, or subscription state.

## Discipline
- Tests are pinned: pricing-constant tests assert exact numbers, not
  ranges or approximate matches.
- A red test blocks moving to the next `SPECS.md` item. Do not comment
  out a failing test to "come back to it" — fix it or log it in
  `BLOCKED.md`.
- Run the full suite before ticking any box in `SPECS.md`, not just the
  test for that box — regressions count against the item that caused
  them, not just the one it broke.
