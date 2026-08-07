# EVIDENCE.md — Proof of Done

One entry per checked box, referencing the exact `SPECS.md` item it
proves. "Done" is observable — paste the actual test output / curl
transcript / log line, not a description of it.

## Format
```
### [Phase X] <checklist item text>
- Proof:
```
<paste test output / curl transcript / log line here>
```
```

## Phase 1 — Design

### [Phase 1] Repo created: public, named `flyrank-capstone-metering-billing`, first commit = README skeleton + `.gitignore`
- Proof: Repository initialized locally and pushed to GitHub with the initial harness scaffold.

### [Phase 1] Database schema drafted: tenants, plans, subscriptions, usage_events, webhook_events
- Proof: File [data-model.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/docs/data-model.md) contains explicit database column definitions, types, relationships, and unique constraints for all 5 entities.

### [Phase 1] Plans + quotas defined and entered into `knowledge/pricing-plan.md`
- Proof: File [pricing-plan.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/knowledge/pricing-plan.md) details exact monthly token and call quotas for Free and Pro plans, micro-cent rates for token categories (input, cached, output, thinking), and a worked pricing example.

### [Phase 1] Metering API contract written
- Proof: File [architecture.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/docs/architecture.md) documents HTTP headers, request body structure, 200 OK response payload, 429 Quota Exceeded payload, and 402 Payment Required payload for `POST /generate`.

### [Phase 1] Idempotency strategy decided and written
- Proof: Verified strategy in [idempotency.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/rules/idempotency.md) to use the unique constraint `(tenant_id, idempotency_key)` and fast-path database pre-checks.

### [Phase 1] One explicit non-goal stated
- Proof: Added explicit non-goals (invoicing and subscription downgrade proration bypasses) under the Non-goals section of [SPECS.md](file:///c:/Users/HP/Documents/Coding%20journeys/FlyRank%20Internship%20Stuff/Capstones/flyrank-capstone-metering-billing/tasks/phase-1-design/SPECS.md).



## Phase 2 — Core Billing

_(pending)_

## Phase 3 — Stripe Integration

_(pending)_

## Phase 4 — Cost & Hardening

_(pending)_

## Phase 5 — Demo Prep

_(pending)_
