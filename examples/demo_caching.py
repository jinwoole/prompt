#!/usr/bin/env python3
"""
Demo script showcasing Redis Caching functionality.

This demo demonstrates:
- Redis connection and configuration
- Basic cache operations (get, set, delete)
- JSON and pickle serialization
- TTL (Time To Live) functionality
- Cache patterns (write-through, write-around, write-back)
- Performance comparison with and without caching
- Cache invalidation strategies
"""
import asyncio
import json
import time
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


class MockRedisClient:
    """Mock Redis client for demonstration when Redis is not available."""
    
    def __init__(self):
        self.data = {}
        self.ttl_data = {}
        
    async def ping(self):
        """Mock ping response."""
        return True
    
    async def set(self, key: str, value: bytes, ex: Optional[int] = None):
        """Mock set operation."""
        self.data[key] = value
        if ex:
            self.ttl_data[key] = datetime.now() + timedelta(seconds=ex)
        return True
    
    async def get(self, key: str) -> Optional[bytes]:
        """Mock get operation."""
        # Check TTL
        if key in self.ttl_data:
            if datetime.now() > self.ttl_data[key]:
                if key in self.data:
                    del self.data[key]
                del self.ttl_data[key]
                return None
        
        return self.data.get(key)
    
    async def delete(self, key: str) -> int:
        """Mock delete operation."""
        if key in self.data:
            del self.data[key]
            if key in self.ttl_data:
                del self.ttl_data[key]
            return 1
        return 0
    
    async def exists(self, key: str) -> int:
        """Mock exists operation."""
        if key in self.ttl_data:
            if datetime.now() > self.ttl_data[key]:
                if key in self.data:
                    del self.data[key]
                del self.ttl_data[key]
                return 0
        return 1 if key in self.data else 0
    
    async def ttl(self, key: str) -> int:
        """Mock TTL operation."""
        if key not in self.data:
            return -2  # Key doesn't exist
        if key not in self.ttl_data:
            return -1  # Key exists but no TTL
        
        remaining = self.ttl_data[key] - datetime.now()
        return max(0, int(remaining.total_seconds()))
    
    async def close(self):
        """Mock close operation."""
        pass


async def get_redis_client():
    """Get Redis client, fallback to mock if Redis unavailable."""
    try:
        from app.cache.redis_client import redis_client, init_redis
        
        if redis_client is None:
            await init_redis()
        
        if redis_client:
            await redis_client.ping()
            return redis_client, False
    except Exception:
        pass
    
    print("⚠️  Redis not available, using mock client for demonstration")
    return MockRedisClient(), True


async def demo_basic_cache_operations():
    """Demonstrate basic cache operations."""
    print_banner("Basic Cache Operations Demo")
    
    redis, is_mock = await get_redis_client()
    
    print(f"✓ Using {'Mock' if is_mock else 'Real'} Redis client")
    
    # Basic set and get operations
    test_data = {
        "string_key": "Hello, Redis!",
        "number_key": 42,
        "dict_key": {"name": "FastAPI", "version": "0.100.0", "features": ["async", "fast", "modern"]},
        "list_key": [1, 2, 3, "four", 5.0]
    }
    
    print(f"\n✓ Setting {len(test_data)} cache entries:")
    
    for key, value in test_data.items():
        # Serialize value based on type
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value).encode('utf-8')
        else:
            serialized_value = str(value).encode('utf-8')
        
        await redis.set(f"demo:{key}", serialized_value)
        print(f"  Set {key}: {str(value)[:50]}")
    
    print(f"\n✓ Retrieving cache entries:")
    
    for key in test_data.keys():
        cached_value = await redis.get(f"demo:{key}")
        if cached_value:
            # Try to deserialize as JSON first, fallback to string
            try:
                decoded_value = json.loads(cached_value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                decoded_value = cached_value.decode('utf-8')
            
            print(f"  Got {key}: {str(decoded_value)[:50]}")
        else:
            print(f"  ✗ {key}: Not found")
    
    # Test cache existence
    print(f"\n✓ Testing cache existence:")
    for key in test_data.keys():
        exists = await redis.exists(f"demo:{key}")
        print(f"  {key}: {'✓ Exists' if exists else '✗ Missing'}")
    
    # Clean up
    for key in test_data.keys():
        await redis.delete(f"demo:{key}")
    
    print(f"\n✓ Cleanup completed")


async def demo_ttl_functionality():
    """Demonstrate TTL (Time To Live) functionality."""
    print_banner("TTL (Time To Live) Demo")
    
    redis, is_mock = await get_redis_client()
    
    # Set values with different TTLs
    ttl_tests = [
        {"key": "short_lived", "value": "Expires in 3 seconds", "ttl": 3},
        {"key": "medium_lived", "value": "Expires in 10 seconds", "ttl": 10},
        {"key": "long_lived", "value": "Expires in 60 seconds", "ttl": 60},
        {"key": "permanent", "value": "Never expires", "ttl": None}
    ]
    
    print(f"✓ Setting cache entries with TTL:")
    
    for test in ttl_tests:
        key = f"ttl_demo:{test['key']}"
        value = test['value'].encode('utf-8')
        
        if test['ttl']:
            await redis.set(key, value, ex=test['ttl'])
            print(f"  {test['key']}: TTL {test['ttl']} seconds")
        else:
            await redis.set(key, value)
            print(f"  {test['key']}: No TTL")
    
    # Check TTL values
    print(f"\n✓ Checking TTL values:")
    
    for test in ttl_tests:
        key = f"ttl_demo:{test['key']}"
        ttl = await redis.ttl(key)
        
        if ttl == -2:
            status = "Key doesn't exist"
        elif ttl == -1:
            status = "No TTL set"
        else:
            status = f"{ttl} seconds remaining"
        
        print(f"  {test['key']}: {status}")
    
    # Wait and check expiration
    if not is_mock:  # Only wait with real Redis for timing accuracy
        print(f"\n✓ Waiting 4 seconds to test expiration...")
        await asyncio.sleep(4)
    else:
        print(f"\n✓ Simulating expiration...")
        # Manually trigger expiration in mock
        await redis.get(f"ttl_demo:short_lived")
    
    print(f"✓ Checking values after expiration:")
    
    for test in ttl_tests:
        key = f"ttl_demo:{test['key']}"
        value = await redis.get(key)
        exists = await redis.exists(key)
        
        if value:
            print(f"  {test['key']}: ✓ Still exists")
        else:
            print(f"  {test['key']}: ✗ Expired/Missing")
    
    # Clean up remaining keys
    for test in ttl_tests:
        await redis.delete(f"ttl_demo:{test['key']}")


async def demo_serialization_methods():
    """Demonstrate different serialization methods."""
    print_banner("Serialization Methods Demo")
    
    redis, is_mock = await get_redis_client()
    
    # Test data with different types
    test_objects = {
        "simple_dict": {"name": "John", "age": 30, "active": True},
        "nested_dict": {
            "user": {"id": 1, "profile": {"bio": "Developer", "skills": ["Python", "FastAPI"]}},
            "metadata": {"created": "2024-01-01", "version": 2}
        },
        "list_of_dicts": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ],
        "complex_types": {
            "datetime": datetime.now().isoformat(),
            "numbers": [1, 2.5, 3],
            "mixed": ["string", 42, True, None]
        }
    }
    
    print(f"✓ Testing JSON serialization:")
    
    for name, obj in test_objects.items():
        key = f"json_demo:{name}"
        
        # Serialize with JSON
        json_data = json.dumps(obj, default=str).encode('utf-8')
        await redis.set(key, json_data)
        
        # Retrieve and deserialize
        cached_data = await redis.get(key)
        if cached_data:
            deserialized = json.loads(cached_data.decode('utf-8'))
            print(f"  {name}: ✓ Success (size: {len(json_data)} bytes)")
        else:
            print(f"  {name}: ✗ Failed")
    
    print(f"\n✓ Testing Pickle serialization:")
    
    # Add some Python-specific objects
    python_objects = {
        "datetime_obj": datetime.now(),
        "timedelta_obj": timedelta(days=7, hours=3),
        "set_obj": {1, 2, 3, 4, 5},
        "tuple_obj": (1, "two", 3.0, True)
    }
    
    for name, obj in python_objects.items():
        key = f"pickle_demo:{name}"
        
        # Serialize with Pickle
        pickle_data = pickle.dumps(obj)
        await redis.set(key, pickle_data)
        
        # Retrieve and deserialize
        cached_data = await redis.get(key)
        if cached_data:
            try:
                deserialized = pickle.loads(cached_data)
                print(f"  {name}: ✓ Success (size: {len(pickle_data)} bytes)")
                print(f"    Original: {obj}")
                print(f"    Cached:   {deserialized}")
            except Exception as e:
                print(f"  {name}: ✗ Deserialization failed: {e}")
        else:
            print(f"  {name}: ✗ Not found")
    
    # Clean up
    for name in test_objects.keys():
        await redis.delete(f"json_demo:{name}")
    for name in python_objects.keys():
        await redis.delete(f"pickle_demo:{name}")


async def demo_cache_patterns():
    """Demonstrate common cache patterns."""
    print_banner("Cache Patterns Demo")
    
    redis, is_mock = await get_redis_client()
    
    # Simulate a slow database operation
    async def slow_database_query(query_id: int) -> Dict[str, Any]:
        """Simulate a slow database query."""
        await asyncio.sleep(0.1)  # Simulate database latency
        return {
            "id": query_id,
            "data": f"Database result for query {query_id}",
            "timestamp": datetime.now().isoformat(),
            "processing_time": 0.1
        }
    
    # Cache-aside pattern (lazy loading)
    async def get_data_with_cache_aside(query_id: int) -> Dict[str, Any]:
        """Implement cache-aside pattern."""
        cache_key = f"cache_aside:query:{query_id}"
        
        # Try to get from cache first
        cached_data = await redis.get(cache_key)
        if cached_data:
            print(f"  Cache HIT for query {query_id}")
            return json.loads(cached_data.decode('utf-8'))
        
        # Cache miss - get from database
        print(f"  Cache MISS for query {query_id} - fetching from DB")
        data = await slow_database_query(query_id)
        
        # Store in cache
        await redis.set(cache_key, json.dumps(data, default=str).encode('utf-8'), ex=300)
        return data
    
    print(f"✓ Testing Cache-Aside Pattern:")
    
    # First request - cache miss
    start_time = time.time()
    result1 = await get_data_with_cache_aside(1)
    time1 = time.time() - start_time
    
    # Second request - cache hit
    start_time = time.time()
    result2 = await get_data_with_cache_aside(1)
    time2 = time.time() - start_time
    
    print(f"  First request: {time1:.3f}s (cache miss)")
    print(f"  Second request: {time2:.3f}s (cache hit)")
    print(f"  Performance improvement: {time1/time2:.1f}x faster")
    
    # Write-through pattern
    async def update_data_write_through(query_id: int, new_data: Dict[str, Any]):
        """Implement write-through pattern."""
        cache_key = f"write_through:query:{query_id}"
        
        # Update database (simulated)
        print(f"  Writing to database for query {query_id}")
        await asyncio.sleep(0.05)  # Simulate DB write
        
        # Update cache immediately
        await redis.set(cache_key, json.dumps(new_data, default=str).encode('utf-8'), ex=300)
        print(f"  Updated cache for query {query_id}")
    
    print(f"\n✓ Testing Write-Through Pattern:")
    
    new_data = {
        "id": 2,
        "data": "Updated data with write-through",
        "timestamp": datetime.now().isoformat(),
        "version": 2
    }
    
    await update_data_write_through(2, new_data)
    
    # Verify cache was updated
    cached_result = await redis.get("write_through:query:2")
    if cached_result:
        print(f"  ✓ Cache updated successfully")
    
    # Write-behind (write-back) pattern simulation
    write_behind_queue = []
    
    async def update_data_write_behind(query_id: int, new_data: Dict[str, Any]):
        """Implement write-behind pattern."""
        cache_key = f"write_behind:query:{query_id}"
        
        # Update cache immediately
        await redis.set(cache_key, json.dumps(new_data, default=str).encode('utf-8'), ex=300)
        print(f"  Updated cache immediately for query {query_id}")
        
        # Queue for later database write
        write_behind_queue.append({"key": cache_key, "data": new_data})
        print(f"  Queued database write for query {query_id}")
    
    async def process_write_behind_queue():
        """Process queued writes."""
        while write_behind_queue:
            item = write_behind_queue.pop(0)
            print(f"  Processing queued write: {item['key']}")
            await asyncio.sleep(0.05)  # Simulate DB write
    
    print(f"\n✓ Testing Write-Behind Pattern:")
    
    new_data_wb = {
        "id": 3,
        "data": "Updated data with write-behind",
        "timestamp": datetime.now().isoformat(),
        "version": 1
    }
    
    await update_data_write_behind(3, new_data_wb)
    print(f"  Queue size: {len(write_behind_queue)}")
    
    # Process queue
    await process_write_behind_queue()
    print(f"  Queue processed, size: {len(write_behind_queue)}")
    
    # Clean up
    cleanup_keys = [
        "cache_aside:query:1",
        "write_through:query:2", 
        "write_behind:query:3"
    ]
    for key in cleanup_keys:
        await redis.delete(key)


async def demo_cache_invalidation():
    """Demonstrate cache invalidation strategies."""
    print_banner("Cache Invalidation Demo")
    
    redis, is_mock = await get_redis_client()
    
    # Set up test data
    test_data = {
        "user:1": {"name": "John Doe", "email": "john@example.com", "role": "admin"},
        "user:2": {"name": "Jane Smith", "email": "jane@example.com", "role": "user"},
        "user:3": {"name": "Bob Wilson", "email": "bob@example.com", "role": "user"},
        "config:app": {"version": "1.0.0", "debug": False, "max_users": 1000},
        "stats:daily": {"visits": 1500, "users": 250, "date": "2024-01-01"}
    }
    
    print(f"✓ Setting up test data:")
    for key, value in test_data.items():
        await redis.set(f"invalidation_demo:{key}", json.dumps(value).encode('utf-8'), ex=3600)
        print(f"  Set {key}")
    
    # Time-based invalidation (TTL)
    print(f"\n✓ Time-based invalidation:")
    
    # Set short TTL data
    await redis.set(
        "invalidation_demo:temp:session", 
        json.dumps({"user_id": 1, "token": "abc123"}).encode('utf-8'), 
        ex=2
    )
    print(f"  Set temporary session with 2-second TTL")
    
    # Manual invalidation
    print(f"\n✓ Manual invalidation:")
    
    # Update user data and invalidate cache
    updated_user = {"name": "John Doe Jr.", "email": "john.jr@example.com", "role": "admin"}
    await redis.set(f"invalidation_demo:user:1", json.dumps(updated_user).encode('utf-8'), ex=3600)
    print(f"  Updated user:1 data")
    
    # Pattern-based invalidation
    print(f"\n✓ Pattern-based invalidation simulation:")
    
    # Simulate clearing all user caches
    user_keys = ["user:1", "user:2", "user:3"]
    for key in user_keys:
        full_key = f"invalidation_demo:{key}"
        deleted = await redis.delete(full_key)
        print(f"  Invalidated {key}: {'✓ Success' if deleted else '✗ Not found'}")
    
    # Tag-based invalidation simulation
    print(f"\n✓ Tag-based invalidation simulation:")
    
    # Set data with "tags" in key names
    tagged_data = {
        "product:1:tag:electronics": {"name": "Laptop", "price": 999},
        "product:2:tag:electronics": {"name": "Phone", "price": 599},
        "product:3:tag:books": {"name": "Python Guide", "price": 29},
        "product:4:tag:electronics": {"name": "Tablet", "price": 399}
    }
    
    for key, value in tagged_data.items():
        await redis.set(f"invalidation_demo:{key}", json.dumps(value).encode('utf-8'), ex=3600)
    
    print(f"  Set {len(tagged_data)} tagged products")
    
    # Simulate invalidating all electronics
    electronics_keys = [key for key in tagged_data.keys() if "electronics" in key]
    for key in electronics_keys:
        full_key = f"invalidation_demo:{key}"
        await redis.delete(full_key)
    
    print(f"  Invalidated {len(electronics_keys)} electronics products")
    
    # Check remaining data
    remaining = 0
    for key in tagged_data.keys():
        full_key = f"invalidation_demo:{key}"
        exists = await redis.exists(full_key)
        if exists:
            remaining += 1
    
    print(f"  Remaining products: {remaining}")
    
    # Event-driven invalidation example
    print(f"\n✓ Event-driven invalidation example:")
    
    class CacheInvalidator:
        def __init__(self, redis_client):
            self.redis = redis_client
        
        async def on_user_updated(self, user_id: int):
            """Invalidate user-related caches."""
            patterns = [
                f"user:{user_id}",
                f"user:{user_id}:profile",
                f"user:{user_id}:preferences",
                f"stats:user:{user_id}"
            ]
            
            for pattern in patterns:
                key = f"invalidation_demo:{pattern}"
                await self.redis.delete(key)
                print(f"    Invalidated {pattern}")
        
        async def on_config_changed(self):
            """Invalidate configuration caches."""
            config_keys = ["config:app", "config:database", "config:cache"]
            for key in config_keys:
                full_key = f"invalidation_demo:{key}"
                await self.redis.delete(full_key)
                print(f"    Invalidated {key}")
    
    invalidator = CacheInvalidator(redis)
    
    # Simulate events
    await invalidator.on_user_updated(1)
    await invalidator.on_config_changed()
    
    # Final cleanup
    await redis.delete("invalidation_demo:config:app")
    await redis.delete("invalidation_demo:stats:daily")


async def main():
    """Run the complete Redis caching demo."""
    print_banner("Redis Caching Demo")
    print("This demo showcases caching patterns and strategies with Redis.")
    
    try:
        # Basic cache operations
        await demo_basic_cache_operations()
        
        # TTL functionality
        await demo_ttl_functionality()
        
        # Serialization methods
        await demo_serialization_methods()
        
        # Cache patterns
        await demo_cache_patterns()
        
        # Cache invalidation
        await demo_cache_invalidation()
        
        print_banner("Redis Caching Demo Complete")
        print("✓ All caching features demonstrated successfully!")
        print("\nKey Features Covered:")
        print("- Basic cache operations (get, set, delete)")
        print("- TTL (Time To Live) functionality")
        print("- JSON and Pickle serialization")
        print("- Cache patterns (cache-aside, write-through, write-behind)")
        print("- Cache invalidation strategies")
        print("- Performance optimization benefits")
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        raise


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())