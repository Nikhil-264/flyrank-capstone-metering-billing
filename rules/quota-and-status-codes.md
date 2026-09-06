# Rule: Quota Enforcement & Status Codes

## Order of operations
`current_usage + requested_usage → compare to plan limit → allow or reject`
Quota is checked **before** the action is allowed, not after (capstone
glossary: "Enforced before the action, not after").

## Status codes — do not blur these
- `429 Too Many Requests` → usage quota exceeded (plan allowance used
  up for the period). The response **carries a `Retry-After` header**
  (integer seconds until `current_period_end`, else the first instant
  of next calendar month) and a message stating the limit and current
  usage. Implemented in `app/api/errors.py` via
  `QuotaExceededException.retry_after`.
- `402 Payment Required` → the plan itself doesn't allow the action
  (e.g. lapsed/unpaid subscription) — distinct from "you used your
  quota." Message must say what upgrading/paying would fix.
- Every rejection message must be specific enough that a machine caller
  (or a human reading logs) can tell which of the two happened and why,
  without inspecting the database.

## Boundary honesty (capstone §2's "boundary honesty" hard part)
- **Boundary Rule**: A request is allowed if `current_usage + requested_usage <= limit`.
- **Behavior**:
  - A request that brings the usage exactly to the limit (e.g., request #1000 of 1000, or adding tokens that exactly hit `max_tokens`) is **allowed**.
  - A request that would exceed the limit (e.g., request #1001 of 1000, or adding tokens that would result in `current_tokens + requested_tokens > max_tokens`) is **rejected** with a `429 Too Many Requests` status code.
- This rule is applied consistently across both API call limits and AI token limits.
- **Simultaneous Enforcement**: Generation requests (`POST /generate`) count against both the **AI token quota** (based on requested tokens) and the **API call quota** (counting as exactly 1 API call). If either limit is exceeded, the request is rejected with a `429` status code.
- **Order**: the quota check runs **before** the usage event is persisted. A rejected request writes no row.
- **Concurrency**: `QuotaService.check_quota` locks the tenant's `subscriptions` row `FOR UPDATE` for the life of the request transaction, so two simultaneous `/generate` calls for one tenant are serialized at the boundary and cannot both pass at 999/1000. Proven by `tests/test_quota.py::test_quota_boundary_is_race_safe`.
- **Shared counting**: "used so far this period" for both enforcement and `GET /usage` comes from one module, `app/services/usage_query.py`, so the two never disagree.


