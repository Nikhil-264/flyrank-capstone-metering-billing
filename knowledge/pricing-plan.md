# pricing-plan.md — Business Guardrail (External Knowledge Base)

This is business logic that doesn't live in code comments — it lives
here, and code points back to it (see `rules/money-math.md`). Update
this file first when a pricing rule changes; code changes follow it,
never the other way around.

## Plans & quotas (capstone §4)
| Plan | API calls / month | AI tokens / month |
|---|---|---|
| Free | 1,000 | 100,000 |
| Pro | higher (define exact number in `app/config/pricing.py` once set — keep this table in sync) |

## Token pricing rule (capstone §4.3, §14 Phase-4 resource)
`total_cost = price(input) + price(cached_input) + price(output) + price(reasoning_as_output)`

- Input tokens and cached input tokens are **separate line items** —
  cached input is priced lower than fresh input. Never sum them first
  and apply one rate.
- Reasoning ("thinking") tokens are billed **as output tokens** — same
  rate as output, not a separate free or discounted category, and not
  omitted from the total.
- Categories cannot be added together and priced as one bucket — each
  has its own per-unit rate, summed only *after* pricing, not before.
- Ground truth for how a real provider structures this: Gemini API
  pricing (cached input + thinking tokens) — see `docs/curated-resources.md`
  Phase 4 row. Use it to sanity-check the *shape* of the rule, not to
  copy literal dollar figures — this project's rates are simulated and
  pinned in `app/config/pricing.py` + tested in the matching test file.

## API-call pricing
Flat monthly cost model tied to plan tier — API calls are metered by
count, not tokens. Exact per-call rate (if any beyond quota
enforcement) is pinned in `app/config/pricing.py`.

## Worked example (fill in once rates are pinned)
```
Tenant used: 10,000 input tokens, 2,000 cached input tokens,
             3,000 output tokens, 500 reasoning tokens.
Expected total = (10,000 × input_rate) + (2,000 × cached_rate)
                + (3,000 × output_rate) + (500 × output_rate)
```
This worked example must match a pinned test exactly — see
`rules/testing-standard.md`.
