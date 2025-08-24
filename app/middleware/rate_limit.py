"""Rate limiting middleware using Redis."""
import time
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.cache.redis_client import get_redis
from app.config import config
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis for storage."""
    
    def __init__(
        self,
        app,
        calls: int = None,
        period: int = None,
        identifier: Callable = None
    ):
        super().__init__(app)
        self.calls = calls or config.security.rate_limit_requests
        self.period = period or config.security.rate_limit_window
        self.identifier = identifier or self._default_identifier
    
    def _default_identifier(self, request: Request) -> str:
        """Default identifier using client IP."""
        # Try to get real IP from X-Forwarded-For header (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Fallback to direct client IP
            client_ip = request.client.host if request.client else "unknown"
        
        return f"rate_limit:{client_ip}"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        redis_client = get_redis()
        
        # If Redis is not available, skip rate limiting
        if not redis_client:
            logger.warning("Redis not available, skipping rate limiting")
            return await call_next(request)
        
        # Get rate limit key for this client
        key = self.identifier(request)
        current_time = int(time.time())
        window_start = current_time - self.period
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries (outside current window)
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration for the key
            pipe.expire(key, self.period)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Get current request count (after removing old entries)
            current_requests = results[1]
            
            # Check rate limit
            if current_requests >= self.calls:
                # Calculate remaining time until window reset
                remaining_time = self.period
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.calls,
                        "window": self.period,
                        "retry_after": remaining_time
                    },
                    headers={"Retry-After": str(remaining_time)}
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.calls - current_requests - 1))
            response.headers["X-RateLimit-Reset"] = str(current_time + self.period)
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions (like 429)
            raise
        except Exception as e:
            # Log error and continue without rate limiting
            logger.error(f"Rate limiting error: {e}")
            return await call_next(request)


class IPRateLimitMiddleware(RateLimitMiddleware):
    """Rate limiting by IP address."""
    
    def __init__(self, app, calls: int = None, period: int = None):
        super().__init__(app, calls, period, self._ip_identifier)
    
    def _ip_identifier(self, request: Request) -> str:
        """Identifier based on IP address."""
        return self._default_identifier(request)


class UserRateLimitMiddleware(RateLimitMiddleware):
    """Rate limiting by authenticated user."""
    
    def __init__(self, app, calls: int = None, period: int = None):
        super().__init__(app, calls, period, self._user_identifier)
    
    def _user_identifier(self, request: Request) -> str:
        """Identifier based on authenticated user."""
        # Try to get user from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"rate_limit:user:{user_id}"
        
        # Fallback to IP-based limiting
        return self._default_identifier(request)


def create_rate_limiter(
    calls: int = None,
    period: int = None,
    per_user: bool = False
) -> RateLimitMiddleware:
    """
    Create a rate limiting middleware.
    
    Args:
        calls: Number of calls allowed per period
        period: Time period in seconds
        per_user: If True, limit per user; if False, limit per IP
        
    Returns:
        Configured rate limiting middleware
    """
    calls = calls or config.security.rate_limit_requests
    period = period or config.security.rate_limit_window
    
    if per_user:
        return lambda app: UserRateLimitMiddleware(app, calls, period)
    else:
        return lambda app: IPRateLimitMiddleware(app, calls, period)