# Rule: Idempotent Metering

This is the heart of the capstone (capstone §2, §4). Treat it as the
highest-scrutiny code path in the repo.

## Contract
- Every billable request carries a client-supplied idempotency key.
- `MeterService.record(tenant, type, qty, idempotency_key)`:
  - If the key has been seen for this tenant → return the **original**
    result. Do not create a new `usage_event` row. Do not recompute.
  - If the key is new → store the `usage_event`, then run the quota
    check.
- The idempotency key + tenant pair must be unique at the database
  level (a unique constraint), not just checked in application code —
  a race between two concurrent retries must still land on one row.

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
