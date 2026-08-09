# FlyRank Capstone — Usage Metering & Billing Engine

A multi-tenant service that meters API/AI-token usage, enforces plan
quotas, computes cost, and syncs subscription state with Stripe (test
mode). Built as a Harness-Engineered project — see `AGENTS.md` for the
environment this was built inside.

> This README is a skeleton, filled in progressively as phases
> complete. Do not backfill it at the end — keep it honest as you go.

## Status
See root `SPECS.md` for the live checklist. Current phase: **Phase 1 —
Design**.

## Architecture

<!-- Diagram goes here once docs/architecture-diagram.md is rendered.
     Pointer: docs/architecture.md is the source of truth for the flow. -->

For the security model (specifically, the header-supplied identity scope and exclusion of real API key authentication), see the [Security scope section in docs/architecture.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/docs/architecture.md#security-scope-documented-decision-not-an-oversight).

## Stack
Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy + Alembic · pytest ·
Stripe (test mode) — full rationale in `docs/stack.md`.

## Setup (must work from a clean clone)
```bash
git clone <this-repo-url>
cd flyrank-capstone-metering-billing
cp .env.example .env        # fill in Stripe TEST keys
docker compose up --build
```

## Run
```bash
docker compose up
```

## Test
```bash
docker compose run --rm api pytest
```

## Local Stripe webhook testing
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger checkout.session.completed
```

## Repo map
| Path | Purpose |
|---|---|
| `AGENTS.md` | Agent coordinator / router — read first |
| `SPECS.md` | Master Definition-of-Done checklist |
| `tasks/<phase>/SPECS.md` | Per-phase implementation checklist |
| `docs/` | Architecture & data-model pointer docs |
| `rules/` | Hard constraints (money math, idempotency, quotas, Stripe, testing) |
| `knowledge/` | Business guardrails (pricing rules, program constraints) |
| `tech-debt-tracker.md` | Intentional decisions — do not "fix" these |
| `BLOCKED.md` | Open blockers requiring a human |
| `learnings.md` | Generalized findings from building this |
| `EVIDENCE.md` | Proof-of-done per checklist item |
| `BUILDLOG.md` | Honest AI-usage log |
| `capstone.yaml` | Submission manifest |

## Non-goal
See `tasks/phase-1-design/SPECS.md` for the explicit stated non-goal.
