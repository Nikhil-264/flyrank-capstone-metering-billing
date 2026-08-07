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
