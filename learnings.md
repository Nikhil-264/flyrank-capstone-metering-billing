# learnings.md — Generalized Findings

Every session appends here when it learns something that should change
how future sessions behave (not just this one bug). This is how the
harness improves itself. Do not log routine work — only generalizable
findings that should influence a rule, a spec template, or the
coordinator.

## Format
```
### [DATE] <one-line finding>
- Symptom:
- Root cause:
- Systemic fix applied: <which rule/spec/file was updated, and how>
```

## Log

### 2026-08-07 — Event Loop mismatch in asyncpg and pytest-asyncio
- Symptom: pytest runs failed with `InterfaceError: cannot perform operation: another operation is in progress`.
- Root cause: Having a session-scoped `test_engine` and session-scoped `event_loop` fixture alongside default function-scoped tests in `pytest-asyncio` causes connections to be accessed across mismatched event loops, leading to asyncpg connection protocol state errors.
- Systemic fix applied: Made `test_engine` and database fixtures function-scoped so they are created and executed on the same event loop as the individual test, and removed custom session-scoped event loop overrides.

### 2026-08-07 — Postgres deadlock during concurrent uncommitted inserts
- Symptom: pytest hung/stuck on the concurrency test indefinitely.
- Root cause: Postgres unique index verification blocks concurrent inserts of the same key until the transaction that first inserted the key commits or rolls back. Running both tasks in `asyncio.gather()` before committing either transaction caused the second task to block on the database, while the test loop blocked waiting for `gather` to finish, resulting in a deadlock.
- Systemic fix applied: Redesigned the concurrency test to insert the first record, schedule a background task to commit the first session after a small delay (50ms), and then execute the second insert. The second insert blocks on flush until the first commits, at which point it unblocks, throws unique constraint violation, and cleanly falls back to the committed row.

### 2026-08-07 — Event Loop mismatch during FastAPI integration testing
- Symptom: Integration tests using `httpx.AsyncClient` failed with `RuntimeError: Task got Future attached to a different loop` or `InterfaceError: cannot perform operation: another operation is in progress`.
- Root cause: The FastAPI app's dependency injection container was resolving `get_db` using the global `engine` instance created on a different event loop (at import time), while the pytest fixtures created a function-scoped `test_engine` on the test loop. Mismatched event loops accessing database connections leads to connection state errors.
- Systemic fix applied: Configured the `client` fixture in `conftest.py` to automatically override FastAPI's `get_db` dependency with a function that yields the shared test session `db` fixture. This ensures both test code and API route handlers share the exact same `AsyncSession` instance, event loop, and connection transaction.

### 2026-08-07 — AI tokens count towards the API call quota limit
- Symptom: API call boundary test failed on request #1001 with 200 instead of 429.
- Root cause: The `/generate` endpoint records usage as a `UsageEvent` of `type="ai_token"` (tracking tokens used). When checking the API calls quota limit, the quota check was only summing the quantities of events of `type="api_call"`, and thus ignored the generate requests which are also API calls.
- Systemic fix applied: Modified `QuotaService.check_quota()` to count total API calls as the sum of `quantity` of `api_call` events plus the count of `ai_token` event rows (representing generation requests).

### 2026-08-08 — Stripe current_period_start/end fields moved to subscription item level in newer API versions
- Symptom: Real Stripe webhook delivery triggers failed on subscription sync with `AttributeError: current_period_start`.
- Root cause: In Stripe API version `2025-03-31.basil` and newer (including Dahlia `2026-07-29.dahlia` used by the test account), `current_period_start` and `current_period_end` are no longer top-level attributes of the Subscription object. Instead, they have been moved down to individual subscription items to support mixed-interval subscriptions.
- Systemic fix applied: Created `_get_period_dates()` helper function in `stripe.py` webhook to extract timestamps from the first item under `items.data[0]` if they are missing at the subscription top-level, and added unit tests covering both legacy and new structures.

### 2026-08-09 — Optional API parameters defaulting under strict positive validation
- Symptom: Enabling strict positive quantity validation (`quantity > 0`) in the `/generate` endpoint caused existing quota boundary tests to fail with 400 Bad Request when they omitted `mock_usage`.
- Root cause: If `mock_usage` is omitted, requested token quantities default to 0. Rejecting zero quantities causes valid simulator requests (intended to test count-based API quotas) to be blocked.
- Systemic fix applied: Defaulted to `input_tokens = 1` when `mock_usage` is omitted. This ensures that the generated event records a positive quantity (>0) and satisfies the validation rule, while still rejecting explicit zero-quantity mock payloads (e.g. all 0 tokens).
