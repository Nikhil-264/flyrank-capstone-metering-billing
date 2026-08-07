# Curated Resources — Per Phase

Reference material only — never copy code verbatim from these; use
them to sanity-check the *shape* of a rule (see
`knowledge/pricing-plan.md` for how this applies to token pricing).

| Phase | Topic | Use for |
|---|---|---|
| 1 | REST API design, DB schema design for multi-tenant SaaS | Design doc grounding |
| 2 | Idempotency key patterns, rate-limiting/quota patterns | `rules/idempotency.md`, `rules/quota-and-status-codes.md` |
| 3 | Stripe Checkout + Webhooks docs, Stripe CLI docs | `rules/stripe-webhooks.md` |
| 4 | Gemini API pricing (cached input + thinking/reasoning tokens) | Shape check for `knowledge/pricing-plan.md` — not literal rates |
| 5 | Writing a README a stranger can follow; Mermaid diagram syntax | `README.md`, `docs/architecture-diagram.md` |

Add specific links here as you actually use them, with a one-line note
on what you took from each — this becomes part of `BUILDLOG.md`'s
honesty trail if AI helped summarize any of them.
