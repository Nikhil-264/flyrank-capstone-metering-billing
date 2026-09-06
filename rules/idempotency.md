# Rule: Idempotent Metering

This is the heart of the capstone (capstone §2, §4). Treat it as the
highest-scrutiny code path in the repo.

## Contract
- Every billable request carries a client-supplied idempotency key.
- Order of operations in `POST /generate` (`app/api/generate.py`):
  1. If the `(tenant, key)` pair has been seen → return the **original**
     result. No new `usage_event`, no recompute.
  2. If the key is new → run the **quota check first**
     (`QuotaService.check_quota`), then `MeterService.record()` persists
     the event. Fail fast: a request that will be rejected must never
     write a row. (This is a deliberate refinement of the capstone's
     store-then-check sketch — see `tech-debt-tracker.md`.)
- `MeterService.record(tenant, type, qty, idempotency_key)` itself is
  still idempotent (pre-check + constraint) so it is safe to call from
  any path.
- The idempotency key + tenant pair must be unique at the database
  level (`uq_tenant_idempotency_key`), not just checked in application
  code — a race between two concurrent retries must still land on one
  row. The same discipline applies to Stripe webhook events, keyed by
  Stripe event id (`webhook_events` PK); a concurrent duplicate delivery
  that loses the insert race is treated as a duplicate, not a 500.

## Required tests (do not consider this rule "implemented" without
these passing)
- Same request sent twice with the same key → exactly one `usage_event`
  row; both HTTP responses are identical.
- Two concurrent requests with the same key (simulated race) → still
  exactly one row.
- Same tenant, different keys → two rows (proves we're not
  over-deduplicating).
- Different tenants, same key → two rows (keys are scoped per tenant).

## Do not
- Do not "clean up" the unique constraint or the pre-check as
  redundant — the pre-check is a fast path; the constraint is the
  correctness guarantee. Both stay.
