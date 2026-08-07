# app/config/pricing.py
# Rates are defined in micro-cents (1 cent = 10,000 micro-cents, $1 = 1,000,000 micro-cents)
# Pinned pricing rules as defined in knowledge/pricing-plan.md

INPUT_TOKEN_RATE = 10          # 10 micro-cents per token ($1.00 / M tokens)
CACHED_INPUT_TOKEN_RATE = 2     # 2 micro-cents per token ($0.20 / M tokens)
OUTPUT_TOKEN_RATE = 30         # 30 micro-cents per token ($3.00 / M tokens)
REASONING_TOKEN_RATE = 30      # 30 micro-cents per token (billed as output rate)

API_CALL_RATE = 0              # Flat monthly model (0 micro-cents per call)
