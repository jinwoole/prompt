"""
Integration tests for the Enterprise FastAPI Application with real PostgreSQL.
These tests require a running PostgreSQL database.
"""
import os
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
import sys

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for real database testing BEFORE importing anything else
os.environ["USE_MOCK_DB"] = "false"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Use test database port
os.environ["DB_NAME"] = "fastapi_test_db"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

# Force reload of config by clearing any cached modules
import importlib
import sys
for module_name in list(sys.modules.keys()):
    if module_name.startswith('app.'):
        del sys.modules[module_name]

from app.main import app
from app.models.database import db_manager
from app.models.entities import Base


def check_database_availability():
    """Check if PostgreSQL test database is available."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 5433))
        sock.close()
        return result == 0
    except Exception:
        return False


# Check database availability at module level
if not check_database_availability():
    pytest.skip("PostgreSQL database not available - skipping integration tests", allow_module_level=True)


# Use a simpler approach with the TestClient
client = TestClient(app)


def setup_module():
    """Setup module - this runs once for the entire module."""
    pass  # Setup is handled by the app lifespan


def teardown_module():
    """Teardown module."""
    pass  # Cleanup is handled by the app lifespan


class TestDatabaseIntegration:
    """Integration tests with real PostgreSQL database."""
    
    def setup_method(self):
        """Setup before each test method - clean the database."""
        # Since we can't easily clean async database from sync test, 
        # we'll ensure each test uses unique data or test in isolation
        pass
    
    def test_application_starts(self):
        """Test that the application starts correctly."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Enterprise FastAPI Application" in data["message"]
    
    def test_create_and_retrieve_item(self):
        """Test creating and retrieving an item from real database."""
        # Use unique item name to avoid conflicts
        import time
        unique_name = f"Integration Test Item {int(time.time() * 1000)}"
        
        # Create an item
        item_data = {
            "name": unique_name,
            "price": 99.99,
            "is_offer": True
        }
        
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        assert created_item["name"] == item_data["name"]
        assert created_item["price"] == item_data["price"]
        assert created_item["is_offer"] == item_data["is_offer"]
        assert "id" in created_item
        assert "created_at" in created_item
        assert "updated_at" in created_item
        
        # Retrieve the item
        item_id = created_item["id"]
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 200
        retrieved_item = get_response.json()
        
        assert retrieved_item["id"] == created_item["id"]
        assert retrieved_item["name"] == created_item["name"]
        assert retrieved_item["price"] == created_item["price"]
        
        # Clean up - delete the item
        client.delete(f"/api/v1/items/{item_id}")
    
    def test_update_item_in_database(self):
        """Test updating an item in the real database."""
        import time
        unique_name = f"Original Item {int(time.time() * 1000)}"
        
        # Create an item first
        item_data = {"name": unique_name, "price": 50.0}
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        # Update the item
        update_data = {"name": f"Updated Item {int(time.time() * 1000)}", "price": 75.0}
        item_id = created_item["id"]
        update_response = client.put(f"/api/v1/items/{item_id}", json=update_data)
        assert update_response.status_code == 200
        updated_item = update_response.json()
        
        assert updated_item["name"] == update_data["name"]
        assert updated_item["price"] == update_data["price"]
        assert updated_item["updated_at"] != created_item["updated_at"]
        
        # Clean up
        client.delete(f"/api/v1/items/{item_id}")
    
    def test_delete_item_from_database(self):
        """Test deleting an item from the real database."""
        import time
        unique_name = f"Item to Delete {int(time.time() * 1000)}"
        
        # Create an item first
        item_data = {"name": unique_name, "price": 30.0}
        create_response = client.post("/api/v1/items", json=item_data)
        assert create_response.status_code == 201
        created_item = create_response.json()
        
        # Delete the item
        item_id = created_item["id"]
        delete_response = client.delete(f"/api/v1/items/{item_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 404
    
    def test_search_with_database(self):
        """Test search functionality with real database."""
        import time
        timestamp = int(time.time() * 1000)
        
        # Create test items with unique names
        items_data = [
            {"name": f"Apple iPhone {timestamp}", "price": 999.0},
            {"name": f"Samsung Galaxy {timestamp}", "price": 899.0},
            {"name": f"Apple MacBook {timestamp}", "price": 1299.0},
            {"name": f"Dell Laptop {timestamp}", "price": 799.0},
        ]
        
        created_items = []
        for item_data in items_data:
            response = client.post("/api/v1/items", json=item_data)
            assert response.status_code == 201
            created_items.append(response.json())
        
        try:
            # Search for Apple products
            response = client.get(f"/api/v1/items/search?q=Apple {timestamp}")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 2
            assert all(f"Apple" in item["name"] for item in data["items"])
            
            # Search for Laptop products
            response = client.get(f"/api/v1/items/search?q=Laptop {timestamp}")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["total"] == 1
            assert "Laptop" in data["items"][0]["name"]
        finally:
            # Clean up created items
            for item in created_items:
                client.delete(f"/api/v1/items/{item['id']}")
    
    def test_concurrent_operations(self):
        """Test concurrent database operations."""
        import threading
        import time
        
        timestamp = int(time.time() * 1000)
        results = []
        created_items = []
        
        def create_item(index):
            item_data = {"name": f"Concurrent Item {timestamp}-{index}", "price": float(index)}
            response = client.post("/api/v1/items", json=item_data)
            results.append(response.status_code)
            if response.status_code == 201:
                created_items.append(response.json())
        
        # Create multiple items concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_item, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        try:
            # Verify all operations succeeded
            assert all(status == 201 for status in results)
            assert len(created_items) == 5
        finally:
            # Clean up created items
            for item in created_items:
                client.delete(f"/api/v1/items/{item['id']}")