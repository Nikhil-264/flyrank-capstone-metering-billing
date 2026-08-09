# Phase 5 — Polish & Demo Prep (≈4–6h)

Gate: this is the last phase. When it's checked, root `SPECS.md` and
all five `docs/evaluation-probes.md` probes must also be green — this
phase does not add features, only proves and packages what exists.

## Checklist
- [x] Run all five `docs/evaluation-probes.md` probes manually against
      a freshly-booted instance (`docker compose up` from a clean
      clone) — not just against a long-running dev instance.
- [x] `README.md` complete: architecture diagram, setup instructions a
      stranger can follow, `run:`/`test:` commands verified from clean
      clone.
- [x] `capstone.yaml` filled in accurately (see file header).
- [x] `EVIDENCE.md` complete — every checked box across all phase
      SPECS.md files has a matching evidence entry.
- [x] `BUILDLOG.md` complete — honest AI-usage log, not retrofitted
      from memory; should have been kept running throughout.
- [x] `.env.example` matches every env var actually read by the app —
      no drift.
- [x] Repo hygiene check: no secrets in git history
      (`git log -p | grep -i secret` sanity pass), `.gitignore` covers
      `.env`, `__pycache__/`, `.venv/`.
- [x] `tech-debt-tracker.md` and `learnings.md` reviewed — anything
      learned this phase logged.
- [x] Optional: one stretch goal from `knowledge/ground-rules.md`
      "Exceptional" bar attempted only after everything above is done.

## Evidence
This phase's evidence IS the completeness of `EVIDENCE.md` itself —
no separate entry needed beyond a final "clean clone re-run" transcript.
