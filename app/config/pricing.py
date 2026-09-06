# app/config/pricing.py
# ---------------------------------------------------------------------------
# Pinned pricing constants. Business source of truth: knowledge/pricing-plan.md.
# Change that file first, then these constants, then the matching tests.
#
# UNIT: every cost in this system is an integer count of "micro-cents".
#   1 micro-cent   = 1e-4 cents = 1e-6 USD  (a millionth of a dollar)
#   10,000 micro-cents = 1 cent
#   1,000,000 micro-cents = 1 USD
# Money is NEVER stored or computed as float/Decimal (capstone §3). Conversion
# to a human dollar string happens only at the presentation edge.
# ---------------------------------------------------------------------------

INPUT_TOKEN_RATE = 10          # 10 micro-cents / token  ($1.00 per 1M tokens)
CACHED_INPUT_TOKEN_RATE = 2    # 2 micro-cents / token   ($0.20 per 1M tokens) — cheaper than fresh input
OUTPUT_TOKEN_RATE = 30         # 30 micro-cents / token  ($3.00 per 1M tokens)
REASONING_TOKEN_RATE = 30      # reasoning ("thinking") tokens are billed at the OUTPUT rate

# API calls use a flat, plan-tier model: quota is enforced by count, but there
# is no per-call metered charge. The recurring plan fee (e.g. Pro = $49/mo)
# lives at Stripe and is intentionally NOT surfaced in GET /usage cost, which
# reports metered usage cost only. See README "Limitations".
API_CALL_RATE = 0             # micro-cents per API call
