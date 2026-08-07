# Rule: Stripe Integration (Test Mode Only)

## Mode
- Stripe **test mode only**, forever, for this project. Test cards
  (e.g. `4242 4242 4242 4242`) with any future expiry. Never switch to
  live mode — there is no reason to for this capstone.
- `STRIPE_SECRET_KEY` (test) and `STRIPE_WEBHOOK_SECRET` (`whsec_...`)
  live only in `.env`, which is git-ignored. A committed key — even a
  test one — is an instant repo-hygiene fail per capstone rules. If one
  is ever committed: rotate it in the Stripe dashboard and rewrite
  history immediately, don't just delete it in a new commit.
- Use the Stripe CLI (`stripe listen --forward-to localhost:<port>`,
  `stripe trigger <event>`) for all local webhook testing. No public
  URL or tunnel needed, none should be added.

## Webhook handler contract
1. Verify the signature against the raw request body using
   `STRIPE_WEBHOOK_SECRET` **before** touching the payload. A bad
   signature → `400`, nothing else happens.
2. Deduplicate by Stripe event ID. A replayed real event → processed
   once; the second delivery is a no-op that still returns 2xx (so
   Stripe doesn't keep retrying).
3. Handle: `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted`. Update tenant plan/status from these
   only — the database mirrors Stripe, it does not originate billing
   truth.
4. Payment truth lives at Stripe. If local state and Stripe ever
   disagree, Stripe wins (see stretch goal: reconciliation job).

## Required tests
- Valid signed event → processed, tenant state updated.
- Forged/invalid signature → `400`, no state change.
- Same valid event delivered twice → processed once (idempotent on
  Stripe event ID, same discipline as `rules/idempotency.md`).
