"""
Real before/after benchmark for the ix_usage_events_tenant_type_created index.

Seeds MANY tenants (so a per-tenant filter actually has to skip rows when
there's no index), then times the exact aggregate query UsageQuery uses,
once with the index present and once with it dropped -- using
EXPLAIN (ANALYZE, FORMAT JSON) so we get Postgres's own execution-time
number, averaged over multiple runs.
"""
import asyncio
import statistics
import time
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.settings import settings

N_TENANTS = 40
ROWS_PER_TENANT = 2500          # 40 * 2500 = 100,000 rows total
RUNS = 15


async def seed(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS bench_events"))
        await conn.execute(text("""
            CREATE TABLE bench_events (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id uuid NOT NULL,
                type varchar(50) NOT NULL,
                quantity integer NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
        """))
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        except Exception:
            pass

    tenant_ids = [str(uuid.uuid4()) for _ in range(N_TENANTS)]
    async with engine.begin() as conn:
        for tid in tenant_ids:
            # Insert in batches via generate_series -- fast bulk insert.
            await conn.execute(text("""
                INSERT INTO bench_events (tenant_id, type, quantity)
                SELECT :tid, 'ai_token', 100
                FROM generate_series(1, :n)
            """), {"tid": tid, "n": ROWS_PER_TENANT})
    return tenant_ids


async def time_query(engine, target_tenant, label):
    times = []
    async with engine.connect() as conn:
        # warmup
        await conn.execute(text(
            "SELECT coalesce(sum(quantity),0) FROM bench_events "
            "WHERE tenant_id = :tid AND type = 'ai_token' AND created_at >= now() - interval '365 days'"
        ), {"tid": target_tenant})
        for _ in range(RUNS):
            res = await conn.execute(text("""
                EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS)
                SELECT coalesce(sum(quantity),0) FROM bench_events
                WHERE tenant_id = :tid AND type = 'ai_token'
                  AND created_at >= now() - interval '365 days'
            """), {"tid": target_tenant})
            plan = res.scalar()
            exec_ms = plan[0]["Execution Time"]
            times.append(exec_ms)
    print(f"{label}: runs={times}")
    print(f"{label}: mean={statistics.mean(times):.3f} ms  "
          f"median={statistics.median(times):.3f} ms  "
          f"min={min(times):.3f} ms  max={max(times):.3f} ms")
    return times


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    print(f"Seeding {N_TENANTS} tenants x {ROWS_PER_TENANT} rows = {N_TENANTS*ROWS_PER_TENANT} rows ...")
    tenant_ids = await seed(engine)
    target = tenant_ids[-1]

    async with engine.begin() as conn:
        await conn.execute(text("ANALYZE bench_events"))

    print("\n=== WITHOUT index (pre-hardening: migration 0001 only) ===")
    without = await time_query(engine, target, "no-index")

    print("\nCreating ix_bench_tenant_type_created (mirrors ix_usage_events_tenant_type_created) ...")
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE INDEX ix_bench_tenant_type_created ON bench_events (tenant_id, type, created_at)"
        ))
        await conn.execute(text("ANALYZE bench_events"))

    print("\n=== WITH index (post-hardening: migration 0002) ===")
    withidx = await time_query(engine, target, "with-index")

    speedup = statistics.mean(without) / statistics.mean(withidx)
    print(f"\n=== RESULT: composite index speeds up the quota/rollup aggregate query "
          f"by {speedup:.1f}x  ({statistics.mean(without):.2f} ms -> {statistics.mean(withidx):.2f} ms) "
          f"across {N_TENANTS*ROWS_PER_TENANT:,} usage_events / {N_TENANTS} tenants ===")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS bench_events"))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
