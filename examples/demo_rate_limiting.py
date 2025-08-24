#!/usr/bin/env python3
"""
Demo script showcasing Rate Limiting functionality.

This demo demonstrates:
- Rate limiting middleware configuration
- Different rate limiting algorithms (token bucket, sliding window)
- Client identification strategies (IP, user, API key)
- Rate limit enforcement and responses
- Rate limit status headers
- Bypass mechanisms for trusted sources
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


class MockRequest:
    """Mock FastAPI Request for demonstration."""
    
    def __init__(self, client_ip: str = "127.0.0.1", path: str = "/api/test", headers: Dict[str, str] = None):
        self.client = type('Client', (), {'host': client_ip})()
        self.url = type('URL', (), {'path': path})()
        self.headers = headers or {}
        self.method = "GET"


class MockRedisClient:
    """Mock Redis client for rate limiting demonstration."""
    
    def __init__(self):
        self.data = {}
        self.ttl_data = {}
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value with TTL check."""
        if key in self.ttl_data and datetime.now() > self.ttl_data[key]:
            if key in self.data:
                del self.data[key]
            del self.ttl_data[key]
            return None
        return self.data.get(key)
    
    async def set(self, key: str, value: bytes, ex: Optional[int] = None):
        """Set value with optional TTL."""
        self.data[key] = value
        if ex:
            self.ttl_data[key] = datetime.now() + timedelta(seconds=ex)
        return True
    
    async def incr(self, key: str) -> int:
        """Increment counter."""
        current = await self.get(key)
        if current is None:
            new_value = 1
        else:
            new_value = int(current.decode()) + 1
        
        # Preserve TTL if it exists
        if key in self.ttl_data:
            await self.set(key, str(new_value).encode(), 
                          ex=int((self.ttl_data[key] - datetime.now()).total_seconds()))
        else:
            await self.set(key, str(new_value).encode())
        
        return new_value
    
    async def expire(self, key: str, seconds: int):
        """Set TTL for existing key."""
        if key in self.data:
            self.ttl_data[key] = datetime.now() + timedelta(seconds=seconds)
        return key in self.data
    
    async def ttl(self, key: str) -> int:
        """Get remaining TTL."""
        if key not in self.data:
            return -2
        if key not in self.ttl_data:
            return -1
        remaining = self.ttl_data[key] - datetime.now()
        return max(0, int(remaining.total_seconds()))


class RateLimiter:
    """Rate limiter with different algorithms."""
    
    def __init__(self, redis_client, calls: int = 100, period: int = 60):
        self.redis = redis_client
        self.calls = calls
        self.period = period
    
    def get_identifier(self, request: MockRequest) -> str:
        """Get client identifier."""
        # Check for API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"rate_limit:api_key:{api_key}"
        
        # Check for user ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"rate_limit:user:{user_id}"
        
        # Fallback to IP
        return f"rate_limit:ip:{request.client.host}"
    
    async def fixed_window_limiter(self, request: MockRequest) -> Dict[str, any]:
        """Fixed window rate limiting algorithm."""
        identifier = self.get_identifier(request)
        current_window = int(time.time() // self.period)
        key = f"{identifier}:window:{current_window}"
        
        # Get current count
        current_count = await self.redis.get(key)
        if current_count is None:
            count = 0
        else:
            count = int(current_count.decode())
        
        # Check if limit exceeded
        if count >= self.calls:
            remaining_time = self.period - (int(time.time()) % self.period)
            return {
                "allowed": False,
                "limit": self.calls,
                "remaining": 0,
                "reset_time": remaining_time,
                "algorithm": "fixed_window"
            }
        
        # Increment counter
        new_count = await self.redis.incr(key)
        if new_count == 1:
            await self.redis.expire(key, self.period)
        
        return {
            "allowed": True,
            "limit": self.calls,
            "remaining": max(0, self.calls - new_count),
            "reset_time": self.period - (int(time.time()) % self.period),
            "algorithm": "fixed_window"
        }
    
    async def sliding_window_limiter(self, request: MockRequest) -> Dict[str, any]:
        """Sliding window rate limiting algorithm."""
        identifier = self.get_identifier(request)
        now = time.time()
        pipeline_operations = []
        
        # Create sliding window using multiple fixed windows
        window_size = self.period
        sub_window_size = window_size // 10  # 10 sub-windows
        
        current_requests = 0
        
        # Check requests in each sub-window
        for i in range(10):
            window_start = now - (i * sub_window_size)
            window_key = f"{identifier}:sliding:{int(window_start // sub_window_size)}"
            
            count = await self.redis.get(window_key)
            if count:
                # Weight by how much of this window is in our time range
                weight = min(1.0, (now - window_start) / sub_window_size)
                current_requests += int(count.decode()) * weight
        
        if current_requests >= self.calls:
            return {
                "allowed": False,
                "limit": self.calls,
                "remaining": 0,
                "reset_time": sub_window_size,
                "algorithm": "sliding_window"
            }
        
        # Record this request
        current_window_key = f"{identifier}:sliding:{int(now // sub_window_size)}"
        await self.redis.incr(current_window_key)
        await self.redis.expire(current_window_key, window_size)
        
        return {
            "allowed": True,
            "limit": self.calls,
            "remaining": max(0, int(self.calls - current_requests - 1)),
            "reset_time": sub_window_size,
            "algorithm": "sliding_window"
        }
    
    async def token_bucket_limiter(self, request: MockRequest) -> Dict[str, any]:
        """Token bucket rate limiting algorithm."""
        identifier = self.get_identifier(request)
        key = f"{identifier}:bucket"
        
        now = time.time()
        
        # Get current bucket state
        bucket_data = await self.redis.get(key)
        if bucket_data is None:
            tokens = self.calls
            last_refill = now
        else:
            data = bucket_data.decode().split(":")
            tokens = float(data[0])
            last_refill = float(data[1])
        
        # Calculate tokens to add based on time passed
        time_passed = now - last_refill
        tokens_to_add = time_passed * (self.calls / self.period)
        tokens = min(self.calls, tokens + tokens_to_add)
        
        if tokens < 1:
            return {
                "allowed": False,
                "limit": self.calls,
                "remaining": int(tokens),
                "reset_time": int((1 - tokens) / (self.calls / self.period)),
                "algorithm": "token_bucket"
            }
        
        # Consume one token
        tokens -= 1
        
        # Store updated bucket state
        bucket_state = f"{tokens}:{now}"
        await self.redis.set(key, bucket_state.encode(), ex=self.period * 2)
        
        return {
            "allowed": True,
            "limit": self.calls,
            "remaining": int(tokens),
            "reset_time": 0,
            "algorithm": "token_bucket"
        }


async def demo_rate_limiting_algorithms():
    """Demonstrate different rate limiting algorithms."""
    print_banner("Rate Limiting Algorithms Demo")
    
    redis = MockRedisClient()
    
    # Test different algorithms
    algorithms = [
        ("Fixed Window", "fixed_window_limiter"),
        ("Sliding Window", "sliding_window_limiter"),
        ("Token Bucket", "token_bucket_limiter")
    ]
    
    for algo_name, method_name in algorithms:
        print(f"\n✓ Testing {algo_name} Algorithm:")
        
        # Create rate limiter with low limits for demo
        limiter = RateLimiter(redis, calls=3, period=10)
        method = getattr(limiter, method_name)
        
        request = MockRequest("192.168.1.100")
        
        # Make requests up to the limit
        for i in range(5):
            result = await method(request)
            status = "✓ Allowed" if result["allowed"] else "✗ Blocked"
            print(f"  Request {i+1}: {status} (Remaining: {result['remaining']}, Reset: {result['reset_time']}s)")
            
            if i < 2:  # Small delay between requests
                await asyncio.sleep(0.1)


async def demo_client_identification():
    """Demonstrate different client identification strategies."""
    print_banner("Client Identification Demo")
    
    redis = MockRedisClient()
    limiter = RateLimiter(redis, calls=5, period=60)
    
    # Test different client identification methods
    test_cases = [
        {
            "name": "IP-based identification",
            "request": MockRequest("192.168.1.100"),
            "description": "Basic IP-based rate limiting"
        },
        {
            "name": "API Key identification",
            "request": MockRequest("192.168.1.100", headers={"X-API-Key": "premium-key-123"}),
            "description": "API key-based rate limiting for premium users"
        },
        {
            "name": "User ID identification",
            "request": MockRequest("192.168.1.100", headers={"X-User-ID": "user-456"}),
            "description": "User-based rate limiting for authenticated users"
        },
        {
            "name": "Different IP",
            "request": MockRequest("192.168.1.200"),
            "description": "Different IP should have separate limits"
        }
    ]
    
    print(f"✓ Testing client identification strategies:")
    
    for test_case in test_cases:
        print(f"\n  {test_case['name']}:")
        print(f"  {test_case['description']}")
        
        identifier = limiter.get_identifier(test_case["request"])
        print(f"  Identifier: {identifier}")
        
        # Make a few requests to show separate counters
        for i in range(2):
            result = await limiter.fixed_window_limiter(test_case["request"])
            print(f"    Request {i+1}: Remaining {result['remaining']}/{result['limit']}")


async def demo_rate_limit_responses():
    """Demonstrate rate limit response headers and status codes."""
    print_banner("Rate Limit Responses Demo")
    
    redis = MockRedisClient()
    
    class RateLimitMiddleware:
        """Simplified rate limit middleware for demo."""
        
        def __init__(self):
            self.limiter = RateLimiter(redis, calls=3, period=30)
        
        async def process_request(self, request: MockRequest) -> Dict[str, any]:
            """Process request with rate limiting."""
            result = await self.limiter.fixed_window_limiter(request)
            
            # Standard rate limit headers
            headers = {
                "X-RateLimit-Limit": str(result["limit"]),
                "X-RateLimit-Remaining": str(result["remaining"]),
                "X-RateLimit-Reset": str(int(time.time()) + result["reset_time"])
            }
            
            if not result["allowed"]:
                # Add retry-after header when blocked
                headers["Retry-After"] = str(result["reset_time"])
                return {
                    "status_code": 429,
                    "headers": headers,
                    "body": {
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {result['limit']} per {30} seconds",
                        "retry_after": result["reset_time"]
                    }
                }
            
            return {
                "status_code": 200,
                "headers": headers,
                "body": {"message": "Request successful"}
            }
    
    middleware = RateLimitMiddleware()
    request = MockRequest("203.0.113.1")
    
    print(f"✓ Testing rate limit responses:")
    
    for i in range(5):
        response = await middleware.process_request(request)
        
        print(f"\n  Request {i+1}:")
        print(f"    Status: {response['status_code']}")
        print(f"    Headers:")
        for header, value in response["headers"].items():
            print(f"      {header}: {value}")
        
        if response["status_code"] == 429:
            print(f"    Body: {response['body']}")
            break
        else:
            print(f"    Body: {response['body']}")


async def demo_bypass_mechanisms():
    """Demonstrate rate limit bypass mechanisms."""
    print_banner("Rate Limit Bypass Demo")
    
    redis = MockRedisClient()
    
    class AdvancedRateLimiter(RateLimiter):
        """Rate limiter with bypass mechanisms."""
        
        def __init__(self, redis_client, calls: int = 100, period: int = 60):
            super().__init__(redis_client, calls, period)
            self.trusted_ips = {"127.0.0.1", "10.0.0.0/8", "192.168.0.0/16"}
            self.premium_keys = {"premium-key-123", "enterprise-key-456"}
            self.admin_users = {"admin", "service-account"}
        
        def is_trusted_ip(self, ip: str) -> bool:
            """Check if IP is in trusted range."""
            return ip in self.trusted_ips or ip.startswith("192.168.")
        
        def is_premium_user(self, request: MockRequest) -> bool:
            """Check if user has premium access."""
            api_key = request.headers.get("X-API-Key")
            return api_key in self.premium_keys
        
        def is_admin_user(self, request: MockRequest) -> bool:
            """Check if user is admin."""
            user_id = request.headers.get("X-User-ID")
            return user_id in self.admin_users
        
        async def check_rate_limit(self, request: MockRequest) -> Dict[str, any]:
            """Check rate limit with bypass logic."""
            # Admin users bypass all limits
            if self.is_admin_user(request):
                return {
                    "allowed": True,
                    "bypass_reason": "admin_user",
                    "limit": float('inf'),
                    "remaining": float('inf')
                }
            
            # Trusted IPs get higher limits
            if self.is_trusted_ip(request.client.host):
                # Use 10x normal limit for trusted IPs
                original_calls = self.calls
                self.calls = original_calls * 10
                result = await self.fixed_window_limiter(request)
                result["bypass_reason"] = "trusted_ip"
                self.calls = original_calls
                return result
            
            # Premium users get 5x normal limits
            if self.is_premium_user(request):
                original_calls = self.calls
                self.calls = original_calls * 5
                result = await self.fixed_window_limiter(request)
                result["bypass_reason"] = "premium_user"
                self.calls = original_calls
                return result
            
            # Normal rate limiting
            result = await self.fixed_window_limiter(request)
            result["bypass_reason"] = None
            return result
    
    limiter = AdvancedRateLimiter(redis, calls=2, period=60)
    
    test_cases = [
        {
            "name": "Regular User",
            "request": MockRequest("203.0.113.50"),
            "expected": "Normal rate limits"
        },
        {
            "name": "Trusted IP",
            "request": MockRequest("192.168.1.100"),
            "expected": "10x rate limits"
        },
        {
            "name": "Premium User",
            "request": MockRequest("203.0.113.50", headers={"X-API-Key": "premium-key-123"}),
            "expected": "5x rate limits"
        },
        {
            "name": "Admin User",
            "request": MockRequest("203.0.113.50", headers={"X-User-ID": "admin"}),
            "expected": "No rate limits"
        }
    ]
    
    print(f"✓ Testing bypass mechanisms:")
    
    for test_case in test_cases:
        print(f"\n  {test_case['name']} ({test_case['expected']}):")
        
        # Make several requests to show different limits
        for i in range(3):
            result = await limiter.check_rate_limit(test_case["request"])
            
            bypass_info = f" (Bypass: {result.get('bypass_reason', 'none')})" if result.get('bypass_reason') else ""
            status = "✓ Allowed" if result["allowed"] else "✗ Blocked"
            
            if result["limit"] == float('inf'):
                limit_info = "∞"
            else:
                limit_info = f"{result['remaining']}/{result['limit']}"
            
            print(f"    Request {i+1}: {status} - Remaining: {limit_info}{bypass_info}")


async def demo_rate_limiting_patterns():
    """Demonstrate common rate limiting patterns."""
    print_banner("Rate Limiting Patterns Demo")
    
    redis = MockRedisClient()
    
    print(f"✓ Common Rate Limiting Patterns:")
    
    patterns = [
        {
            "name": "API Gateway Pattern",
            "description": "Different limits per endpoint type",
            "limits": {
                "/api/v1/users": {"calls": 100, "period": 3600},  # 100/hour
                "/api/v1/admin": {"calls": 10, "period": 60},     # 10/minute
                "/api/v1/public": {"calls": 1000, "period": 3600} # 1000/hour
            }
        },
        {
            "name": "User Tier Pattern", 
            "description": "Different limits per user type",
            "limits": {
                "free": {"calls": 100, "period": 86400},      # 100/day
                "premium": {"calls": 10000, "period": 86400}, # 10k/day
                "enterprise": {"calls": 100000, "period": 86400} # 100k/day
            }
        },
        {
            "name": "Burst Protection Pattern",
            "description": "Multiple time windows",
            "limits": {
                "short_burst": {"calls": 10, "period": 60},    # 10/minute
                "medium_burst": {"calls": 100, "period": 3600}, # 100/hour
                "daily_limit": {"calls": 1000, "period": 86400} # 1000/day
            }
        }
    ]
    
    for pattern in patterns:
        print(f"\n  {pattern['name']}:")
        print(f"  {pattern['description']}")
        
        for limit_type, config in pattern["limits"].items():
            calls = config["calls"]
            period = config["period"]
            period_name = "second" if period == 1 else f"{period} seconds"
            if period == 60:
                period_name = "minute"
            elif period == 3600:
                period_name = "hour"
            elif period == 86400:
                period_name = "day"
            
            print(f"    {limit_type}: {calls} requests per {period_name}")
    
    print(f"\n✓ Implementation Strategies:")
    strategies = [
        "Use Redis for distributed rate limiting across multiple servers",
        "Implement sliding window for more accurate rate limiting",
        "Use token bucket for handling burst traffic gracefully",
        "Apply different limits based on endpoint criticality",
        "Implement rate limit headers for client awareness",
        "Use exponential backoff for retry mechanisms",
        "Monitor rate limit metrics for capacity planning"
    ]
    
    for i, strategy in enumerate(strategies, 1):
        print(f"  {i}. {strategy}")


async def main():
    """Run the complete rate limiting demo."""
    print_banner("Rate Limiting Demo")
    print("This demo showcases rate limiting strategies and implementations.")
    
    try:
        # Rate limiting algorithms
        await demo_rate_limiting_algorithms()
        
        # Client identification
        await demo_client_identification()
        
        # Rate limit responses
        await demo_rate_limit_responses()
        
        # Bypass mechanisms
        await demo_bypass_mechanisms()
        
        # Rate limiting patterns
        await demo_rate_limiting_patterns()
        
        print_banner("Rate Limiting Demo Complete")
        print("✓ All rate limiting features demonstrated successfully!")
        print("\nKey Features Covered:")
        print("- Multiple rate limiting algorithms (fixed window, sliding window, token bucket)")
        print("- Client identification strategies (IP, API key, user ID)")
        print("- Standard rate limit response headers")
        print("- Bypass mechanisms for trusted sources")
        print("- Common rate limiting patterns and best practices")
        print("- Redis-based distributed rate limiting")
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        raise


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())