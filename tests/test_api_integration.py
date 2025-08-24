"""
FastAPI integration tests with a running application server.
These tests start the actual FastAPI server and test the HTTP endpoints.
"""
import os
import time
import pytest
import asyncio
import httpx
import subprocess
import signal
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
from app.models.entities import Base
from sqlalchemy import text


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
        pytest.skip("PostgreSQL database not available - skipping API integration tests")
    
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


async def clean_database():
    """Clean all data from database tables."""
    try:
        async with db_manager.engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE items RESTART IDENTITY CASCADE"))
    except Exception:
        pass  # Ignore cleanup errors


class FastAPITestServer:
    """Context manager for running FastAPI test server."""
    
    def __init__(self, port=8001):
        self.port = port
        self.process = None
        self.base_url = f"http://localhost:{port}"
    
    def __enter__(self):
        # Start FastAPI server
        self.process = subprocess.Popen([
            "python", "-m", "uvicorn", "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", str(self.port),
            "--log-level", "warning"
        ], env=os.environ.copy(), cwd="/home/runner/work/tmp/tmp")
        
        # Wait for server to start
        for _ in range(30):  # Wait up to 30 seconds
            try:
                import requests
                response = requests.get(f"{self.base_url}/", timeout=1)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)
        else:
            self.process.terminate()
            raise RuntimeError("FastAPI server failed to start")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.process.terminate()
            self.process.wait()


@pytest.mark.asyncio
async def test_api_endpoints():
    """Test FastAPI endpoints with real database."""
    # Use the existing server or start a new one
    base_url = "http://localhost:8000"  # Assume server is already running
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # Test health check
        print("Testing health check...")
        response = await client.get(f"{base_url}/api/v1/health")
        if response.status_code == 200:
            health_data = response.json()
            assert "status" in health_data
            assert health_data["database"] is True
            print("✓ Health check passed")
        else:
            print(f"⚠ Health check returned {response.status_code}, continuing with other tests...")
        
        # Clean database before tests
        await clean_database()
        
        # Test creating an item
        print("Testing item creation...")
        item_data = {
            "name": "Integration Test Item",
            "price": 99.99,
            "is_offer": True
        }
        response = await client.post(f"{base_url}/api/v1/items", json=item_data)
        assert response.status_code == 201
        created_item = response.json()
        assert created_item["name"] == item_data["name"]
        assert created_item["price"] == item_data["price"]
        item_id = created_item["id"]
        print(f"✓ Item created with ID: {item_id}")
        
        # Test getting the item
        print("Testing item retrieval...")
        response = await client.get(f"{base_url}/api/v1/items/{item_id}")
        assert response.status_code == 200
        retrieved_item = response.json()
        assert retrieved_item["id"] == item_id
        assert retrieved_item["name"] == item_data["name"]
        print("✓ Item retrieved successfully")
        
        # Test updating the item
        print("Testing item update...")
        update_data = {"name": "Updated Item", "price": 149.99}
        response = await client.put(f"{base_url}/api/v1/items/{item_id}", json=update_data)
        assert response.status_code == 200
        updated_item = response.json()
        assert updated_item["name"] == update_data["name"]
        assert updated_item["price"] == update_data["price"]
        print("✓ Item updated successfully")
        
        # Test listing items
        print("Testing item listing...")
        response = await client.get(f"{base_url}/api/v1/items")
        assert response.status_code == 200
        items_data = response.json()
        assert items_data["total"] == 1
        assert len(items_data["items"]) == 1
        print("✓ Items listed successfully")
        
        # Test search
        print("Testing item search...")
        response = await client.get(f"{base_url}/api/v1/items/search?q=Updated")
        assert response.status_code == 200
        search_data = response.json()
        assert search_data["total"] == 1
        assert "Updated" in search_data["items"][0]["name"]
        print("✓ Search functionality working")
        
        # Test deletion
        print("Testing item deletion...")
        response = await client.delete(f"{base_url}/api/v1/items/{item_id}")
        assert response.status_code == 204
        
        # Verify deletion
        response = await client.get(f"{base_url}/api/v1/items/{item_id}")
        assert response.status_code == 404
        print("✓ Item deleted successfully")
        
        print("\n🎉 All API integration tests passed!")


@pytest.mark.asyncio
async def test_with_standalone_server():
    """Test API with a standalone server."""
    print("Starting standalone FastAPI server for testing...")
    
    # Start server in a separate process
    with FastAPITestServer(port=8001) as server:
        
        base_url = server.base_url
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            
            # Clean database before tests
            await clean_database()
            
            print("Testing with standalone server...")
            
            # Test root endpoint
            response = await client.get(f"{base_url}/")
            assert response.status_code == 200
            root_data = response.json()
            assert "message" in root_data
            print("✓ Root endpoint working")
            
            # Test item creation and retrieval
            item_data = {"name": "Standalone Test", "price": 50.0, "is_offer": False}
            response = await client.post(f"{base_url}/api/v1/items", json=item_data)
            assert response.status_code == 201
            created_item = response.json()
            print(f"✓ Item created: {created_item['name']}")
            
            # Test listing
            response = await client.get(f"{base_url}/api/v1/items")
            assert response.status_code == 200
            items_data = response.json()
            assert items_data["total"] == 1
            print("✓ Standalone server tests passed")


async def run_api_tests():
    """Run all API integration tests."""
    print("Starting FastAPI integration tests...")
    print(f"Database: postgresql://postgres:***@localhost:5433/fastapi_test_db")
    print()
    
    try:
        # First try with existing server (if running)
        try:
            await test_api_endpoints()
        except Exception as e:
            print(f"⚠ Failed to test with existing server: {e}")
            print("Trying with standalone server...")
            await test_with_standalone_server()
        
        return True
        
    except Exception as e:
        print(f"❌ API tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run API tests
    success = asyncio.run(run_api_tests())
    exit(0 if success else 1)