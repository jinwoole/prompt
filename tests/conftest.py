"""Shared test configuration and fixtures."""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.models.entities import Base
from app.repositories.user_repository import UserRepository
from app.auth.models import UserCreate


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
SYNC_TEST_DATABASE_URL = "sqlite:///:memory:"



@pytest.fixture(scope="session")
def sync_test_engine():
    """Create synchronous test database engine for FastAPI TestClient."""
    engine = create_engine(
        SYNC_TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sync_db_session(sync_test_engine):
    """Create a synchronous test database session for FastAPI TestClient."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=sync_test_engine)
    session = Session()
    
    try:
        yield session
    finally:
        session.close()
        # Clean up all data after each test
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create a test database session with proper cleanup."""
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Clean up all data after each test to ensure isolation
            await session.rollback()
            # Delete all data from all tables
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="testuser@example.com",
        username="testuser",
        password="testpassword123"
    )
    user = await user_repo.create(user_data)
    await db_session.commit()
    return user