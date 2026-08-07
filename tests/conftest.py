import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.models.base import Base
from app.db.seed import seed_plans

@pytest.fixture
async def test_engine() -> create_async_engine:
    """Create a test engine and initialize the database schema per test."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Drop and recreate all tables for a clean slate
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    # Seed standard plans
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed_plans(session)
        await session.commit()
        
    yield engine
    await engine.dispose()

@pytest.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for a test."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client for calling FastAPI endpoints and override get_db."""
    from httpx import ASGITransport
    from app.main import app
    from app.db.session import get_db

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.pop(get_db, None)
