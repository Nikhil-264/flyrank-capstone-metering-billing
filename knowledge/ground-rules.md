# ground-rules.md — Program Constraints (External Knowledge Base)

Sourced from the FlyRank capstone brief. These are outside the
codebase but govern how the codebase must be built and shipped — the
"context gap" this file exists to close.

## Hard constraints
- $0, no credit card, ever. If any tool/tutorial asks for one, that's
  the wrong path — see `docs/stack.md` for the free alternative.
- Stripe test mode only. Never live mode.
- Secrets (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) in `.env`
  only, git-ignored, never logged.
- One dedicated public GitHub repo, named
  `flyrank-capstone-metering-billing`, separate from any assignments
  repo, public from day one.
- Money as integer cents, never floats.

## Required submission files (repo root)
`README.md`, `capstone.yaml`, `EVIDENCE.md`, `BUILDLOG.md`,
`.env.example` — see each file's own header for what goes in it.

## Evaluation shape (for calibrating effort)
1. Submission pack (machine-checkable: files present, `run:` boots,
   `test:` is green).
2. Five behavioral probes — `docs/evaluation-probes.md`.
3. Rubric, 1–5 × weight: Architecture ×3, Correctness ×3, Resilience
   ×3, Security ×2, AI cost/grounding ×2 (N/A — no AI provider used),
   Testing ×2, Communication ×2.

"Ships" = every `SPECS.md` box + all probes pass. "Solid" = Ships +
rubric avg ≥ 3.5. "Exceptional" = Solid + a genuine stretch goal.
Weights say what's valued: correctness and resilience over feature
count — don't trade core correctness for stretch scope.
