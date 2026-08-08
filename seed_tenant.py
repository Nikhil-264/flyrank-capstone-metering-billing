import asyncio
import uuid
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.db.seed import seed_plans

async def main():
    async with async_session_maker() as session:
        # Seed plans first
        await seed_plans(session)
        await session.commit()
        
        # Check if we have a default tenant
        stmt = select(Tenant).filter_by(name="Demo Tenant")
        res = await session.execute(stmt)
        tenant = res.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(name="Demo Tenant")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"Created Demo Tenant with ID: {tenant.id}")
        else:
            print(f"Demo Tenant already exists with ID: {tenant.id}")
            
        # Check subscription
        sub_stmt = select(Subscription).filter_by(tenant_id=tenant.id)
        sub_res = await session.execute(sub_stmt)
        sub = sub_res.scalar_one_or_none()
        
        if not sub:
            from datetime import datetime, timezone
            sub = Subscription(
                tenant_id=tenant.id,
                plan_id="free",
                status="active",
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc)
            )
            session.add(sub)
            await session.commit()
            print("Created active Free subscription for Demo Tenant.")
        else:
            print(f"Demo Tenant subscription status: {sub.status}, plan: {sub.plan_id}")

if __name__ == "__main__":
    asyncio.run(main())
