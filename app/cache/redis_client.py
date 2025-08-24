"""Redis cache client and utilities."""
import json
import pickle
from typing import Any, Optional, Union
from redis.asyncio import Redis
from app.config import config
import logging

logger = logging.getLogger(__name__)

# Global Redis connection
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    try:
        redis_client = Redis(
            host=config.cache.host,
            port=config.cache.port,
            db=config.cache.db,
            password=config.cache.password,
            decode_responses=False,  # We'll handle encoding ourselves
            socket_connect_timeout=config.cache.socket_connect_timeout,
            socket_timeout=config.cache.socket_timeout,
            retry_on_timeout=True,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        redis_client = None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            redis_client = None


def get_redis() -> Optional[Redis]:
    """Get Redis client instance."""
    return redis_client


class CacheManager:
    """Redis cache manager with common operations."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or get_redis()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        if not self.redis:
            return default
        
        try:
            data = await self.redis.get(key)
            if data is None:
                # Record cache miss
                try:
                    from app.monitoring import record_cache_operation
                    record_cache_operation("get", "miss")
                except ImportError:
                    pass
                return default
            
            # Record cache hit
            try:
                from app.monitoring import record_cache_operation
                record_cache_operation("get", "hit")
            except ImportError:
                pass
            
            # Try to unpickle first (for Python objects)
            try:
                return pickle.loads(data)
            except (pickle.PickleError, TypeError):
                # If unpickling fails, try JSON
                try:
                    return json.loads(data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If both fail, return raw bytes
                    return data
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            # Record cache error
            try:
                from app.monitoring import record_cache_operation
                record_cache_operation("get", "error")
            except ImportError:
                pass
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None,
        json_serializable: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
            json_serializable: Use JSON serialization instead of pickle
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            # Choose serialization method
            if json_serializable:
                data = json.dumps(value, default=str).encode('utf-8')
            else:
                data = pickle.dumps(value)
            
            if expire:
                result = await self.redis.setex(key, expire, data)
            else:
                result = await self.redis.set(key, data)
            
            # Record cache operation
            try:
                from app.monitoring import record_cache_operation
                record_cache_operation("set", "success" if result else "error")
            except ImportError:
                pass
            
            return result
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            # Record cache error
            try:
                from app.monitoring import record_cache_operation
                record_cache_operation("set", "error")
            except ImportError:
                pass
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment, None if error
        """
        if not self.redis:
            return None
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {e}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for cache key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0


# Global cache manager instance
cache = CacheManager()