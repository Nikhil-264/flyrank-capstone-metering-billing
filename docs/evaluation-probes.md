# Evaluation Probes — Layer 2 (Behavioral, Pass/Fail)

These are the exact checks the evaluator runs against the live system
(capstone §12). Treat each as an acceptance test to automate, not just
something to demo manually.

1. **Idempotency probe** — send the same billable request twice with
   one idempotency key → exactly one `usage_event`; second HTTP
   response mirrors the first.
2. **Quota boundary probe** — drive a tenant to its exact quota → the
   boundary request behaves per the documented rule
   (`rules/quota-and-status-codes.md`); the one after returns
   429/402 with a clear message.
3. **Checkout probe** — complete a Stripe test Checkout → webhook flips
   tenant Free → Pro → `GET /usage` shows new limits.
4. **Webhook security probe** — forged webhook (bad signature) → 400,
   nothing changes; replay a real event twice → processed once.
5. **Pricing probe** — pinned pricing tests → cached-input and
   reasoning-token rules produce exact expected totals; `GET /usage`
   matches.

## Rule
Do not mark root `SPECS.md` complete until all five pass against a
running instance (`docker compose up`), not just in isolated unit
tests. Wire each as an automated test AND paste a manual-run transcript
into `EVIDENCE.md` for the corresponding checkbox.
