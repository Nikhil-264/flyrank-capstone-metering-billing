# Rule: Quota Enforcement & Status Codes

## Order of operations
`current_usage + requested_usage → compare to plan limit → allow or reject`
Quota is checked **before** the action is allowed, not after (capstone
glossary: "Enforced before the action, not after").

## Status codes — do not blur these
- `429 Too Many Requests` → usage quota exceeded (plan allowance used
  up for the period). Include a `Retry-After` where meaningful and a
  message stating the limit and current usage.
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


