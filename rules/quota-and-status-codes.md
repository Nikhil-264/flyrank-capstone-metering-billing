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
- Explicitly test and document behavior at exactly the limit (request
  #1000 of 1000), one under (#999), and one over (#1001). Pick one
  documented rule (e.g. "the request that would exceed the limit is
  rejected; the request that exactly reaches the limit is allowed") and
  hold to it consistently — inconsistent boundary handling is a
  correctness bug, not a style choice.
