# Phase 3 — Stripe Integration (≈6–9h)

Gate to pass before Phase 4 starts: a Stripe test Checkout, run
end-to-end via the CLI, flips a tenant from Free to Pro and `GET
/usage` reflects it.

Follow `rules/stripe-webhooks.md` exactly. Test mode only. Never
commit a key — see `knowledge/ground-rules.md`.

## Checklist
- [x] Stripe test account connected; test Products/Prices created for
      Free/Pro (Free may be a no-op / $0 price).
- [x] `POST /checkout` (or equivalent) creates a Stripe Checkout
      Session in test mode, returns the session URL.
- [x] `stripe listen --forward-to localhost:<port>` wired into local
      dev docs (`docs/stack.md` or README "Local dev" section).
- [x] ⚓ Webhook handler verifies signature before touching payload;
      bad signature → 400, no state change.
- [x] Handles `checkout.session.completed` → creates/updates
      `subscription` row, tenant plan flips.
- [x] Handles `customer.subscription.updated` and
      `.deleted` → tenant plan/status updated accordingly.
- [x] Dedup by Stripe event ID: replayed event processed once, still
      returns 2xx on the replay.
- [x] `GET /usage` (or `/plan`) reflects the new plan immediately after
      webhook processing — no manual DB edit needed to demo this.

## Evidence
Paste: (1) `stripe trigger checkout.session.completed` log output,
(2) before/after `GET /usage` showing the plan change, (3) a forged
signature test result — into `EVIDENCE.md` under "Phase 3".
