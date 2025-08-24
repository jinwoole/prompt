"""
Simplified integration tests for PostgreSQL connectivity.
Tests database operations directly without FastAPI TestClient to avoid event loop conflicts.
"""
import os
import pytest
import asyncio
import httpx
from contextlib import asynccontextmanager
import sys
import socket

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for real database testing
os.environ["USE_MOCK_DB"] = "false"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"
os.environ["DB_NAME"] = "fastapi_test_db"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

from app.models.database import db_manager
from app.models.entities import Base, Item
from app.repositories.item_repository import ItemRepository
from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
from sqlalchemy import text, select


def check_database_availability():
    """Check if PostgreSQL test database is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5433))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
async def setup_test_database():
    """Setup and teardown test database."""
    if not check_database_availability():
        pytest.skip("PostgreSQL database not available - skipping direct database tests")
    
    try:
        await db_manager.initialize()
        
        # Create tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield
        
    except Exception as e:
        pytest.skip(f"Database setup failed: {e}")
    finally:
        # Clean up
        try:
            if db_manager.engine:
                async with db_manager.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await db_manager.close()
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture(autouse=True)
async def clean_database():
    """Clean database before each test."""
    if db_manager.engine and db_manager.is_connected:
        try:
            async with db_manager.engine.begin() as conn:
                await conn.execute(text("TRUNCATE TABLE items RESTART IDENTITY CASCADE"))
        except Exception as e:
            print(f"Failed to clean database: {e}")


@pytest.mark.asyncio
async def test_database_connection():
    """Test basic database connectivity."""
    # Test database connection
    async with db_manager.get_session() as session:
        result = await session.execute(text("SELECT 1 as test"))
        assert result.scalar() == 1
    
    print("✓ Database connection test passed")


@pytest.mark.asyncio
async def test_table_creation():
    """Test that tables are created properly."""
    async with db_manager.get_session() as session:
        # Check if items table exists
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'items'
            );
        """))
        assert result.scalar() is True
    
    print("✓ Table creation test passed")


@pytest.mark.asyncio
async def test_item_repository_crud():
    """Test CRUD operations with ItemRepository."""
    async with db_manager.get_session() as session:
        repo = ItemRepository(session)
        
        # Test CREATE
        item_data = ItemCreate(name="Test Item", price=99.99, is_offer=True)
        created_item = await repo.create(item_data)
        assert created_item.name == "Test Item"
        assert created_item.price == 99.99
        assert created_item.is_offer is True
        assert created_item.id is not None
        
        # Test READ
        retrieved_item = await repo.get(created_item.id)
        assert retrieved_item is not None
        assert retrieved_item.name == "Test Item"
        
        # Test UPDATE
        update_data = ItemUpdate(name="Updated Item", price=149.99)
        updated_item = await repo.update(created_item.id, update_data)
        assert updated_item.name == "Updated Item"
        assert updated_item.price == 149.99
        
        # Test DELETE
        deleted = await repo.delete(created_item.id)
        assert deleted is True
        
        # Verify deletion
        deleted_item = await repo.get(created_item.id)
        assert deleted_item is None
    
    print("✓ CRUD operations test passed")


@pytest.mark.asyncio
async def test_search_functionality():
    """Test search functionality."""
    async with db_manager.get_session() as session:
        repo = ItemRepository(session)
        
        # Create test items
        await repo.create(ItemCreate(name="Apple iPhone", price=999.99))
        await repo.create(ItemCreate(name="Samsung Galaxy", price=899.99))
        await repo.create(ItemCreate(name="Apple MacBook", price=1299.99))
        
        # Test search
        search_results = await repo.search("Apple")
        assert len(search_results.items) == 2
        assert search_results.total == 2
        assert all("Apple" in item.name for item in search_results.items)
    
    print("✓ Search functionality test passed")


@pytest.mark.asyncio
async def test_pagination():
    """Test pagination functionality."""
    async with db_manager.get_session() as session:
        repo = ItemRepository(session)
        
        # Create multiple items
        for i in range(10):
            await repo.create(ItemCreate(name=f"Item {i}", price=float(i * 10)))
        
        # Test pagination
        page1 = await repo.get_all(PaginationParams(page=1, limit=5))
        assert len(page1.items) == 5
        assert page1.total == 10
        assert page1.page == 1
        assert page1.pages == 2
        
        page2 = await repo.get_all(PaginationParams(page=2, limit=5))
        assert len(page2.items) == 5
        assert page2.page == 2
    
    print("✓ Pagination test passed")


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent database operations."""
    import asyncio
    
    async def create_item(session, index):
        repo = ItemRepository(session)
        return await repo.create(ItemCreate(name=f"Concurrent Item {index}", price=float(index)))
    
    # Create multiple items concurrently
    async with db_manager.get_session() as session:
        tasks = [create_item(session, i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(item.id is not None for item in results)
    
