# tech-debt-tracker.md — Intentional Decisions Log

Kept separate from `docs/` on purpose: this is the "why we did the
counterintuitive thing" record, not the source of truth for how the
system behaves. If an agent is ever tempted to "clean up" one of these,
it must read the entry first and leave it alone unless the entry itself
is superseded here.

## Format
```
### [DATE] <decision>
- Why: 
- What it looks like in code: <file path>
- Do NOT "fix" this because:
- Revisit when:
```

## Log

### Pre-build baseline
- Decision: Money is stored as integer cents/micro-units everywhere,
  never `float`/`Decimal` display types, even where it looks like it adds
  a conversion step.
  - Why: floats lose precision on currency math (capstone constraint,
    §3). This is not an oversight — do not "simplify" to float.
  - Do NOT "fix" this by rounding to floats for readability.

- Decision: AI token usage is simulated (random/fixed counts), no real
  model call, no AI API key anywhere in this repo.
  - Why: capstone explicitly meters numbers, not model outputs (§7).
  - Do NOT "fix" this by wiring in a live AI provider — it's out of
    scope and reintroduces cost/security surface for no credit.

- Decision: Core scope frozen at 2 plans / 2 usage types / 1 billable
  endpoint. Invoicing, proration, overage billing intentionally absent
  from core.
  - Why: capstone §7 realistic-scope constraint; stretch goals live in
    `tasks/stretch-goals/SPECS.md` and are only started after every core
    box in root `SPECS.md` is green.
  - Do NOT "fix" this by adding stretch features mid-core-build.

### 2026-09-06 — Quota check runs BEFORE persisting the usage event
- Decision: `POST /generate` does dedupe → quota check → persist, not the
  capstone's store-then-check sketch (§5 diagram).
- Why: a request that will be rejected must not leave a `usage_event`
  row. `MeterService.record()` stays independently idempotent, so no
  correctness is lost. `rules/idempotency.md` documents the refined order.
- Do NOT "fix" this by moving the write ahead of the quota check to match
  the diagram literally.

### 2026-09-06 — One usage_event per /generate call (no separate api_call row)
- Decision: `/generate` writes a single `type='ai_token'` row that counts
  as 1 API call AND N tokens; it does not also emit a `type='api_call'`
  row.
- Why: capstone §7 says "creates *a* usage event" (singular); the two
  "usage types" are quota dimensions, not a mandate for two rows. A
  second row would also force `(tenant_id, idempotency_key, type)` into
  the unique constraint. `type='api_call'` rows are still first-class for
  bulk metering and are tested in `tests/test_metering.py`.
- What it looks like in code: `app/services/usage_query.py`.
- Do NOT "fix" this by making the endpoint emit two rows.

### 2026-09-06 — `cost_microcents` column name kept despite the unit being micro-USD
- Decision: the money unit is 1e-6 USD (10,000 = 1 cent). The column /
  field name `cost_microcents` is retained rather than renamed.
- Why: it is part of the documented API response contract and appears in
  submitted `EVIDENCE.md` transcripts. The precise definition is pinned
  in `app/config/pricing.py`, `knowledge/pricing-plan.md`, and the README.
- Do NOT "fix" this with a rename that breaks the response contract.

### 2026-09-06 — Reconciliation runs in-process via APScheduler
- Decision: the nightly job runs inside the API process, not via an
  external scheduler/queue.
- Why: single-instance demo; keeps the `$0` stack. `app/jobs/runner.py`
  gives it retries + a durable `job_runs` record + a CRITICAL alert, which
  is what the shared-requirement #3 "background job" bar asks for.
- Revisit when: the service runs more than one replica (then the job
  would fire once per replica).
