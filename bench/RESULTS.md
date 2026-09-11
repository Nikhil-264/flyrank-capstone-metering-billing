# Benchmark results

Real, reproducible measurements behind the resume-bullet numbers. Both scripts run
against the real `docker compose` Postgres instance (`app/config/settings.py`
`DATABASE_URL`) and print the raw numbers below — nothing here is estimated.

Run them yourself:
```bash
docker compose up -d db
docker compose run --rm --no-deps api python bench/index_benchmark.py
docker compose run --rm --no-deps api python bench/race_condition_benchmark.py
```

## 1. `race_condition_benchmark.py` — the FOR UPDATE quota-boundary fix

Seeds a tenant sitting at 999/1000 API calls, fires two truly concurrent boundary
requests at it, and checks whether both were allowed (an overcount: the tenant ends up
at 1001/1000 instead of 1000/1000). Compares the current `QuotaService.check_quota`
(which takes `SELECT ... FOR UPDATE` on the subscription row) against an identical copy
of the check with that lock removed — i.e. exactly the code path this project shipped
before the concurrency-hardening pass. 40 trials per mode.

```
Running 40 concurrent-boundary trials per mode ...

BEFORE (no FOR UPDATE lock): 39/40 trials overcounted the 1000-call boundary (97.5%)
AFTER  (FOR UPDATE lock): 0/40 trials overcounted the 1000-call boundary (0.0%)

=== RESULT: quota-boundary overcount rate under concurrent load: 97.5% -> 0.0% after adding the row lock (40 trials/mode) ===
```

**Resume number:** quota-boundary overcount rate under concurrent load, **97.5% → 0%**
across 40 trials.

## 2. `index_benchmark.py` — `ix_usage_events_tenant_type_created`

Seeds 40 tenants × 2,500 rows (100,000 `usage_events` rows total), then runs the exact
aggregate query shape `UsageQuery` uses for quota checks and `GET /usage` rollups
(`SUM/COUNT ... WHERE tenant_id = $1 AND type = $2 AND created_at >= $3`) via
`EXPLAIN (ANALYZE, FORMAT JSON)` — 15 timed runs after a warmup — once with only the
`0001` migration's schema (no composite index) and once with the `0002` index added.

```
=== WITHOUT index (pre-hardening: migration 0001 only) ===
no-index: mean=6.252 ms  median=6.207 ms  min=5.702 ms  max=7.822 ms

=== WITH index (post-hardening: migration 0002) ===
with-index: mean=0.454 ms  median=0.449 ms  min=0.357 ms  max=0.642 ms

=== RESULT: composite index speeds up the quota/rollup aggregate query by 13.8x
    (6.25 ms -> 0.45 ms) across 100,000 usage_events / 40 tenants ===
```

**Resume number:** quota/rollup query latency, **~13x faster (6.25ms → 0.45ms)** at
100K+ events across 40 tenants.

## Captured

Both runs above were executed on 2026-09-11 against `main` @ commit `e83906f`
(the "rubric-hardening" state), inside the project's own Docker Compose Postgres
(`postgres:16-alpine`), via `docker compose run --rm --no-deps api python bench/...`.
