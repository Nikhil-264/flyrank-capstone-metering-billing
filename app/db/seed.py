from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.subscription import Subscription

async def seed_plans(db: AsyncSession) -> None:
    """
    Seed standard plans (Free, Pro) if they do not exist.
    """
    result = await db.execute(select(Plan))
    existing_plans = {p.id for p in result.scalars().all()}

    plans = [
        Plan(id="free", name="Free Plan", max_api_calls=1000, max_tokens=100000),
        Plan(id="pro", name="Pro Plan", max_api_calls=100000, max_tokens=10000000),
    ]

    for plan in plans:
        if plan.id not in existing_plans:
            db.add(plan)

    await db.flush()
