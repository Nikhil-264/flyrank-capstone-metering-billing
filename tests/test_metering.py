import pytest
import uuid
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.services.meter_service import MeterService

async def create_test_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    # Refresh to load generated ID
    await db.refresh(tenant)
    return tenant

@pytest.mark.asyncio
async def test_meter_service_record_basic_api_call(db: AsyncSession):
    tenant = await create_test_tenant(db, "Tenant 1")

    # Record API call
    event = await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="api_call",
        quantity=1,
        idempotency_key="api-key-1"
    )
    await db.commit()

    assert event.id is not None
    assert event.tenant_id == tenant.id
    assert event.type == "api_call"
    assert event.quantity == 1
    assert event.idempotency_key == "api-key-1"
    assert event.cost_microcents == 0  # 0 cost for API calls as per config

@pytest.mark.asyncio
async def test_meter_service_record_token_cost_math(db: AsyncSession):
    tenant = await create_test_tenant(db, "Tenant 2")

    # Record AI token usage
    event = await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="ai_token",
        quantity=15500,
        idempotency_key="token-key-1",
        token_input=10000,
        token_cached_input=2000,
        token_output=3000,
        token_reasoning=500
    )
    await db.commit()

    # Worked example in pricing-plan.md:
    # Expected total = (10,000 * 10) + (2,000 * 2) + (3,000 * 30) + (500 * 30)
    #                = 100,000 + 4,000 + 90,000 + 15,000
    #                = 209,000 micro-cents (0.209 cents)
    assert event.cost_microcents == 209000

@pytest.mark.asyncio
async def test_meter_service_deduplication_sequential(db: AsyncSession):
    tenant = await create_test_tenant(db, "Tenant 3")

    # Send first request
    event1 = await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="ai_token",
        quantity=100,
        idempotency_key="dup-key-1",
        token_input=100
    )
    await db.commit()

    # Send second request with identical key
    event2 = await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="ai_token",
        quantity=200,  # different quantity to check if it's ignored
        idempotency_key="dup-key-1",
        token_input=200
    )
    await db.commit()

    # Verify same row returned and quantity is unchanged
    assert event1.id == event2.id
    assert event2.quantity == 100
    assert event2.token_input == 100

    # Verify database has exactly one row
    stmt = select(func.count(UsageEvent.id)).filter_by(tenant_id=tenant.id)
    result = await db.execute(stmt)
    count = result.scalar()
    assert count == 1

@pytest.mark.asyncio
async def test_meter_service_scoping_different_keys_same_tenant(db: AsyncSession):
    tenant = await create_test_tenant(db, "Tenant 4")

    # First key
    await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="api_call",
        quantity=1,
        idempotency_key="key-A"
    )
    # Second key
    await MeterService.record(
        db=db,
        tenant_id=tenant.id,
        type="api_call",
        quantity=1,
        idempotency_key="key-B"
    )
    await db.commit()

    # Verify database has two rows
    stmt = select(func.count(UsageEvent.id)).filter_by(tenant_id=tenant.id)
    result = await db.execute(stmt)
    assert result.scalar() == 2

@pytest.mark.asyncio
async def test_meter_service_scoping_same_key_different_tenants(db: AsyncSession):
    tenantA = await create_test_tenant(db, "Tenant A")
    tenantB = await create_test_tenant(db, "Tenant B")

    # Same key for Tenant A
    await MeterService.record(
        db=db,
        tenant_id=tenantA.id,
        type="api_call",
        quantity=1,
        idempotency_key="shared-key"
    )
    # Same key for Tenant B
    await MeterService.record(
        db=db,
        tenant_id=tenantB.id,
        type="api_call",
        quantity=1,
        idempotency_key="shared-key"
    )
    await db.commit()

    # Verify both records exist
    stmtA = select(func.count(UsageEvent.id)).filter_by(tenant_id=tenantA.id)
    resultA = await db.execute(stmtA)
    assert resultA.scalar() == 1

    stmtB = select(func.count(UsageEvent.id)).filter_by(tenant_id=tenantB.id)
    resultB = await db.execute(stmtB)
    assert resultB.scalar() == 1

@pytest.mark.asyncio
async def test_meter_service_concurrent_race_condition(test_engine):
    """
    Test concurrency using separate DB sessions, simulating concurrent request handlers.
    Both try to write the same idempotency key simultaneously.
    """
    # Create a tenant using a temporary session
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        tenant = await create_test_tenant(session, "Tenant Concurrent")
        tenant_id = tenant.id

    # Create two separate concurrent sessions
    session1 = async_session()
    session2 = async_session()

    try:
        # 1. Start task 1 (it will insert and flush)
        task1 = asyncio.create_task(
            MeterService.record(
                db=session1,
                tenant_id=tenant_id,
                type="ai_token",
                quantity=1000,
                idempotency_key="concurrent-key",
                token_input=1000
            )
        )
        
        # Give task1 a tiny moment to run and flush
        await asyncio.sleep(0.01)
        
        # 2. Schedule a background commit for session1 after a tiny delay
        async def commit_session1():
            await asyncio.sleep(0.05)
            await session1.commit()
            
        commit_task = asyncio.create_task(commit_session1())
        
        # 3. Start task 2 (it will block on flush until session1 commits)
        task2 = asyncio.create_task(
            MeterService.record(
                db=session2,
                tenant_id=tenant_id,
                type="ai_token",
                quantity=2000,
                idempotency_key="concurrent-key",
                token_input=2000
            )
        )
        
        # 4. Wait for both tasks to complete
        res1 = await task1
        res2 = await task2
        await commit_task
        
        # Commit session2 (which should be a no-op/rollback anyway since it failed insert)
        await session2.commit()

        # Both must return the same event ID
        assert res1.id == res2.id
        assert res1.quantity == 1000  # task1 was processed first and committed
        assert res2.quantity == 1000  # task2 was deduped and read task1's committed values

        # Verify database has exactly one row
        async with async_session() as session:
            stmt = select(func.count(UsageEvent.id)).filter_by(tenant_id=tenant_id)
            result = await session.execute(stmt)
            count = result.scalar()
            assert count == 1
    finally:
        await session1.close()
        await session2.close()

