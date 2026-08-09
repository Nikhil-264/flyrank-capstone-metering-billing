# BUILDLOG.md — Honest AI-Usage Log

Keep this running *during* the build, not reconstructed at the end.
Log anything non-trivial the AI wrote, fixed, or got wrong — including
mistakes and how they were caught. This is a credibility document, not
a highlight reel; per Harness doctrine, a caught-and-fixed AI mistake
that produced a rule update is more valuable to log than a clean
one-shot.

## Format
```
### [DATE] <short title>
- Prompted for:
- AI produced:
- Accepted as-is / modified / rejected because:
- If rejected or buggy: root cause + link to learnings.md entry, if any
```

## Log

### 2026-08-07 conftest.py event loop mismatch fix
- Prompted for: Fixing `InterfaceError: cannot perform operation: another operation is in progress` during tests.
- AI produced: Reconfigured conftest database engine and connection fixtures to be function-scoped rather than session-scoped, resolving the asyncpg loop mismatch.
- Accepted as-is / modified / rejected because: Accepted as-is, fixes asyncpg loop mismatch.
- If rejected or buggy: root cause + link to learnings.md entry, if any: event loop mismatch (recorded in learnings.md).

### 2026-08-07 concurrency test deadlock fix
- Prompted for: Fixing hang/stuck pytest on concurrent race condition test.
- AI produced: Redesigned the concurrency test to use a delayed background commit task for session 1, allowing session 2 to block on flush and unblock cleanly when session 1 commits (simulating a real production race condition).
- Accepted as-is / modified / rejected because: Accepted as-is, resolving the postgres uncommitted concurrent insert deadlock.
- If rejected or buggy: root cause + link to learnings.md entry, if any: concurrent uncommitted insert deadlock (recorded in learnings.md).

### 2026-08-07 conftest type hint NameError fix
- Prompted for: Fixing `NameError: name 'AsyncClient' is not defined` error when starting pytest.
- AI produced: Imported `AsyncClient` from `httpx` at the top level of `conftest.py` instead of only inside the fixture definition.
- Accepted as-is / modified / rejected because: Accepted as-is, fixes import dependency for type hinting.

### 2026-08-07 conftest client get_db override fix
- Prompted for: Fixing `RuntimeError` and `InterfaceError` related to mismatched event loops during integration tests.
- AI produced: Overrode FastAPI's `get_db` dependency in the `client` fixture inside `conftest.py` to yield the shared test session `db`.
- Accepted as-is / modified / rejected because: Accepted as-is, guarantees same loop/session usage inside API requests during integration tests.
- If rejected or buggy: root cause + link to learnings.md entry, if any: event loop mismatch in integration tests (recorded in learnings.md).

### 2026-08-07 API calls quota check fix
- Prompted for: Fixing API call quota boundary test failure (request #1001 passing instead of returning 429).
- AI produced: Updated `QuotaService.check_quota()` to count `ai_token` event rows (generation requests) towards the API calls limit.
- Accepted as-is / modified / rejected because: Accepted as-is, accurately aggregates all API requests.
- If rejected or buggy: root cause + link to learnings.md entry, if any: token events not counted as API calls (recorded in learnings.md).

### 2026-08-07 API response float removal and documentation update
- Prompted for: Enforcing integer money end-to-end (changing `cost_cents` float to `cost_microcents` integer in generate response) and documenting simultaneous quota enforcement rules.
- AI produced: Changed `cost_cents` (float) to `cost_microcents` (int) in `app/api/generate.py` response schema, and explicitly documented simultaneous enforcement in `rules/quota-and-status-codes.md`.
- Accepted as-is / modified / rejected because: Accepted as-is, keeps money math strictly integer-based and rules clear.

### 2026-08-08 Webhook signature test helper correction
- Prompted for: Generating signature header in unit tests using stripe library.
- AI produced: Attempted calling `stripe.WebhookSignature.generate_header` (deprecated/removed) and `stripe.Webhook.generate_test_header_string` (unexposed/absent).
- Accepted as-is / modified / rejected because: Rejected due to AttributeErrors. Replaced with a manual HMAC-SHA256 constructor using python's built-in `hmac` and `hashlib` modules for absolute compatibility.

### 2026-08-08 Webhook payload Decimal type serialization error
- Prompted for: Storing Stripe webhook payload dictionary to database JSONB column.
- AI produced: Used `event.to_dict_recursive()` to convert the event object back to dictionary.
- Accepted as-is / modified / rejected because: Rejected because stripe-python parses fee and amount fields as `Decimal` types, which are not JSON-serializable by standard encoders, causing db insert statements to roll back.
- If rejected or buggy: root cause + link to learnings.md entry, if any: Modified code to use `json.loads(payload_bytes.decode('utf-8'))` which maps standard JSON integer/float types directly from Stripe.

### 2026-08-08 Stripe subscription period dates missing (Basil+ API)
- Prompted for: Accessing `current_period_start` and `current_period_end` from subscription object.
- AI produced: Accessed attributes directly on subscription top-level (`sub.current_period_start`).
- Accepted as-is / modified / rejected because: Rejected because Stripe API version `2025-03-31.basil` and newer (e.g. Dahlia) moved billing period fields down to individual items (`sub.items.data[0]`).
- If rejected or buggy: root cause + link to learnings.md entry, if any: Root cause detailed in learnings.md. Created `_get_period_dates()` helper function.

### 2026-08-09 CostService and pricing hardening implementation
- Prompted for: Implementing `CostService.price()`, updating `MeterService.record()` to use it, adding tenant existence verification in `/generate`, and validating positive quantity constraints.
- AI produced: Created `CostService`, updated `MeterService`, added global `ValueError` handler in `errors.py`, added tenant and header validation to `/generate`.
- Accepted as-is / modified / rejected because: Accepted with minor adjustments. The initial implementation rejected `requested_tokens == 0` for all calls, causing existing quota boundary tests (which omitted `mock_usage` and defaulted to 0 tokens) to fail with 400 Bad Request.
- If rejected or buggy: root cause + link to learnings.md entry, if any: Omitted `mock_usage` defaulting to 0 tokens was rejected. Modified code to default to 1 token when `mock_usage` is omitted, resolving the test failures (detailed in learnings.md).

### 2026-08-09 Phase 5 Startup automation, packaging, & Stripe reconciliation stretch goal
- Prompted for: Automating migrations/seeding in docker compose on startup, updating README and capstone.yaml, performing EVIDENCE.md completeness audit, and implementing a Stripe reconciliation script with unit tests.
- AI produced: Updated `docker-compose.yml` container command, created `reconcile_stripe.py` script and `tests/test_reconciliation.py`, updated `README.md` and `capstone.yaml`, logged the EVIDENCE.md audit process violation in `learnings.md`.
- Accepted as-is / modified / rejected because: Accepted as-is. All unit tests ran and passed cleanly.


