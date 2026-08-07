# Rule: Money & Token Pricing Math

## Currency
- All money is stored and computed as **integer cents** (or
  micro-units for sub-cent token pricing). Never `float`.
- Conversion to a human-readable dollar string happens only at the
  presentation edge (API response formatting), never in storage or
  intermediate calculation.
- Pinned pricing constants live in one config module (see
  `docs/architecture.md` for the current path) — not scattered as
  magic numbers.

## Token categories (see `knowledge/pricing-plan.md` for the actual
rates and worked examples)
- Input tokens, cached input tokens, output tokens, and reasoning
  tokens are **priced separately** — they cannot be summed and then
  priced as one bucket.
- Cached input tokens are cheaper than fresh input tokens.
- Reasoning ("thinking") tokens are billed as output tokens — they are
  not a separate free category and not a separate price tier.
- Every pricing rule must have a pinned test with a hand-computed
  expected total. If you can't hand-compute the expected value, the
  rule isn't understood well enough to encode yet — go re-read
  `knowledge/pricing-plan.md`.

## Non-negotiable
Any PR/commit that introduces a float for a money or token-price value
is a bug, full stop. Fix at the type level (integer cents), not with a
rounding call.
