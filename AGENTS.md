# AGENTS.md — Coordinator (Usage Metering & Billing Engine)

You are the Environment Engineer's agent on a FlyRank capstone: a multi-tenant
usage metering + quota + billing service. Money and limits. Bugs here cost
real money. Read this file first, every session. It is a router, not an
encyclopedia — under 100 lines on purpose.

## Prime directives
1. Never fix a bug quietly by hand. If you made a mistake, update the rule or
   spec that allowed it (see `learnings.md`), then fix the code.
2. Never plan and build in the same turn. Planning produces/updates
   `SPECS.md`. Building executes an already-checked-in spec.
3. Store all money as integer cents. Never floats. See `rules/money-math.md`.
4. If you hit an external blocker (Stripe outage, missing credential, unclear
   requirement) — STOP. Log it to `BLOCKED.md`. Do not guess.
5. "Done" = observable: a green test, a curl transcript, a log line pasted
   into `EVIDENCE.md`. Never a feeling.

## Where things live (pointer, not prose — code is truth)
| Need | Go to |
|---|---|
| Current task checklist | `tasks/<phase>/SPECS.md` |
| System architecture | `docs/architecture.md` → points into `app/` |
| Data model | `docs/data-model.md` → points into `app/models/` |
| Idempotency rules | `rules/idempotency.md` |
| Money/token pricing rules | `rules/money-math.md`, `knowledge/pricing-plan.md` |
| Quota / status-code rules | `rules/quota-and-status-codes.md` |
| Stripe webhook rules | `rules/stripe-webhooks.md` |
| Test coverage bar | `rules/testing-standard.md` |
| Intentional weirdness (don't "fix" it) | `tech-debt-tracker.md` |
| Blocked / can't proceed | `BLOCKED.md` |
| Session learnings | `learnings.md` |
| Proof-of-done per checkbox | `EVIDENCE.md` |
| AI-usage honesty log | `BUILDLOG.md` |

## Workflow (the Ralph Loop, one task = one fresh chat)
1. Read this file + the active `tasks/<phase>/SPECS.md`.
2. Check the repo state yourself (or via a subagent) before assuming anything.
3. Implement the single highest-priority unchecked item.
4. Validate observably (run the test, hit the endpoint, check the DB row).
5. Tick the box in `SPECS.md`, paste proof into `EVIDENCE.md`.
6. Write a verbose commit. Update `learnings.md` if you learned something
   generalizable. Update `BUILDLOG.md` if AI wrote/fixed something non-trivial.
7. If blocked, write `BLOCKED.md` and stop — do not invent a workaround.

## Stack (locked — see `docs/stack.md` for rationale)
Python 3.12 · FastAPI · PostgreSQL (Docker) · SQLAlchemy + Alembic ·
pytest · Stripe test mode + Stripe CLI. No AI API key needed — tokens are
simulated counts.

## Definition of Done
The master checklist is `SPECS.md` at repo root, mirroring capstone §6.
Do not mark the project done until every box there is ticked and every
Layer-2 probe in `docs/evaluation-probes.md` passes.

## Scope discipline
2 plans (Free/Pro) · 2 usage types (API calls, AI tokens) · 1 billable
endpoint (`POST /generate`). No invoicing/proration/overage in core — those
are stretch goals, tracked separately in `tasks/stretch-goals/SPECS.md` and
only touched after every core box is green.
