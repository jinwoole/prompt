#!/usr/bin/env python3
"""
Enterprise FastAPI Application Demo - Robust Version

This demo showcases the enterprise-grade features and architecture,
with graceful handling of missing external services like PostgreSQL and Redis.
"""
import asyncio
import json
from datetime import datetime


def print_banner(title):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def demo_configuration():
    """Demonstrate configuration management."""
    print_banner("Configuration Management Demo")
    
    try:
        from app.config import config
        
        print(f"✓ Application: {config.title} v{config.version}")
        print(f"✓ Environment: {config.environment}")
        print(f"✓ Debug Mode: {config.debug}")
        print(f"✓ Database URL: {config.database.url}")
        print(f"✓ Logging Level: {config.logging.level}")
        print(f"✓ Pool Size: {config.database.pool_size}")
        print(f"✓ CORS Origins: {len(config.security.cors_origins)} configured")
        print(f"✓ Rate Limit: {config.security.rate_limit_requests} requests per {config.security.rate_limit_window}s")
        
    except Exception as e:
        print(f"✗ Configuration demo failed: {e}")


def demo_error_handling():
    """Demonstrate error handling."""
    print_banner("Error Handling Demo")
    
    try:
        from app.utils.errors import BusinessLogicError, ValidationError, DatabaseError
        
        # Create error instances
        errors = [
            BusinessLogicError("Invalid business operation", {"code": "BL001"}),
            ValidationError("Invalid input data", "name", {"pattern": "required"}),
            DatabaseError("Connection failed", "create_item", {"timeout": 30}),
        ]
        
        for error in errors:
            print(f"✓ {error.__class__.__name__}: {error.message}")
            if hasattr(error, 'details') and error.details:
                print(f"  Details: {error.details}")
                
    except ImportError as e:
        print(f"✗ Error handling demo failed: {e}")


def demo_logging():
    """Demonstrate logging capabilities."""
    print_banner("Logging System Demo")
    
    try:
        from app.utils.logging import setup_logging, get_logger
        
        # Setup logging
        setup_logging()
        print("✓ Logging system initialized")
        
        # Get logger and demonstrate different levels
        logger = get_logger("demo")
        
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.debug("This is a debug message")
        
        print("✓ Log messages sent (check console output)")
        
    except ImportError as e:
        print(f"✗ Logging demo failed: {e}")


async def demo_database():
    """Demonstrate database functionality with graceful failure handling."""
    print_banner("Database Connection Demo")
    
    try:
        from app.models.database import db_manager
        
        print("🔍 Attempting database connection...")
        
        # Initialize database
        await db_manager.initialize()
        print(f"✓ Database initialized: {db_manager.is_connected}")
        
        # Health check
        healthy = await db_manager.health_check()
        print(f"✓ Database health check: {healthy}")
        
        # Close connection
        await db_manager.close()
        print("✓ Database connection closed")
        
    except Exception as e:
        print(f"⚠️  Database unavailable: {str(e)[:100]}...")
        print("   This is expected if PostgreSQL is not running")
        print("   The application can run without a database for development")
        print("   💡 To set up database: docker compose up -d postgres")


async def demo_cache():
    """Demonstrate cache functionality with graceful failure handling."""
    print_banner("Cache System Demo")
    
    try:
        from app.cache.redis_client import get_redis
        
        print("🔍 Attempting Redis connection...")
        
        redis_client = get_redis()
        if redis_client:
            # Test basic operations
            await redis_client.set("demo_key", "demo_value")
            value = await redis_client.get("demo_key")
            print(f"✓ Redis test successful: {value}")
            
            await redis_client.delete("demo_key")
            print("✓ Cache operations working")
        else:
            print("⚠️  Redis client not available")
            
    except Exception as e:
        print(f"⚠️  Redis unavailable: {str(e)[:100]}...")
        print("   This is expected if Redis is not running")
        print("   The application falls back to in-memory caching")
        print("   💡 To set up Redis: docker compose up -d redis")


async def demo_services():
    """Demonstrate service layer functionality with mock data."""
    print_banner("Service Layer Demo")
    
    try:
        from app.services.item_service import ItemService
        from app.repositories.item_repository import ItemRepository
        from app.models.schemas import ItemCreate, ItemUpdate, PaginationParams
        
        print("🔍 Testing service layer with mock data...")
        
        # Initialize service (will work without database in memory mode)
        repository = ItemRepository()
        service = ItemService(repository)
        print("✓ Service initialized")
        
        # Create sample items
        items_to_create = [
            ItemCreate(name="Enterprise Laptop", price=1299.99, is_offer=False),
            ItemCreate(name="Wireless Mouse", price=49.99, is_offer=True),
            ItemCreate(name="Mechanical Keyboard", price=149.99, is_offer=False),
        ]
        
        created_items = []
        for item_data in items_to_create:
            try:
                item = await service.create_item(item_data)
                created_items.append(item)
                print(f"✓ Created: {item.name} (ID: {item.id})")
            except Exception as e:
                print(f"✗ Failed to create {item_data.name}: {e}")
        
        # List all items
        if created_items:
            pagination = PaginationParams(page=1, limit=10)
            result = await service.get_items(pagination)
            print(f"✓ Retrieved {len(result.items)} items (total: {result.total})")
            
            # Search items
            search_result = await service.search_items("laptop", pagination)
            print(f"✓ Search for 'laptop': {len(search_result.items)} results")
        
    except ImportError as e:
        print(f"⚠️  Service layer demo skipped: {e}")
        print("   Some service dependencies may not be available")
    except Exception as e:
        print(f"⚠️  Service demo failed: {str(e)[:100]}...")
        print("   This may be due to missing database connection")


def demo_security_features():
    """Demonstrate security features."""
    print_banner("Security Features Demo")
    
    try:
        from app.auth.security import pwd_context, create_access_token
        
        print("✓ Password Security:")
        
        # Test password hashing
        test_password = "SecurePassword123!"
        hashed = pwd_context.hash(test_password)
        is_valid = pwd_context.verify(test_password, hashed)
        
        print(f"  Password hashed: {hashed[:30]}...")
        print(f"  Verification: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        print("\n✓ JWT Token Security:")
        
        # Test token creation
        token = create_access_token(data={"sub": "demo_user", "user_id": 123})
        print(f"  Token created: {token[:30]}...")
        print(f"  Token type: Bearer")
        
    except ImportError as e:
        print(f"⚠️  Security features demo skipped: {e}")


def demo_api_features():
    """Demonstrate API features."""
    print_banner("API Features Demo")
    
    try:
        from app.models.schemas import Item, ItemCreate, PaginatedResponse, HealthCheck
        from datetime import datetime, timezone
        
        print("✓ API Models & Validation:")
        
        # Test item creation model
        item_create = ItemCreate(name="Demo Product", price=99.99, is_offer=True)
        print(f"  ItemCreate: {item_create.name} - ${item_create.price}")
        
        # Test item response model
        item = Item(
            id=1,
            name=item_create.name,
            price=item_create.price,
            is_offer=item_create.is_offer,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        print(f"  Item model: ID {item.id}, Created: {item.created_at.date()}")
        
        # Test pagination model
        pagination = PaginatedResponse.create(
            items=[item],
            total=1,
            page=1,
            limit=10
        )
        print(f"  Pagination: Page {pagination.page}/{pagination.pages}, Total: {pagination.total}")
        
        # Test health check model
        health = HealthCheck(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            database=True,
            version="1.0.0"
        )
        print(f"  Health Check: Status {health.status}, DB: {health.database}")
        
    except ImportError as e:
        print(f"⚠️  API features demo skipped: {e}")


def demo_monitoring_features():
    """Demonstrate monitoring capabilities."""
    print_banner("Monitoring Features Demo")
    
    try:
        from app.monitoring import REQUEST_COUNT, REQUEST_DURATION, get_metrics
        
        print("✓ Metrics Collection:")
        
        # Simulate some metrics
        REQUEST_COUNT.labels(method="GET", endpoint="/api/v1/items", status_code="200").inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/api/v1/items", status_code="201").inc()
        REQUEST_DURATION.labels(method="GET", endpoint="/api/v1/items").observe(0.025)
        
        print("  HTTP request metrics recorded")
        
        # Get metrics output
        metrics_output = get_metrics()
        lines = metrics_output.decode('utf-8').split('\n')
        metrics_count = len([line for line in lines if line and not line.startswith('#')])
        
        print(f"  Metrics available: {metrics_count} data points")
        print("  Prometheus format ready for scraping")
        
    except ImportError as e:
        print(f"⚠️  Monitoring features demo skipped: {e}")


async def main():
    """Run the complete demo with graceful error handling."""
    print_banner("Enterprise FastAPI Application Demo")
    print("This demo showcases the enterprise-grade features and architecture.")
    print("💡 Missing services (PostgreSQL, Redis) are handled gracefully.")
    
    # Configuration demo (always available)
    demo_configuration()
    
    # Logging demo (always available)
    demo_logging()
    
    # Error handling demo (always available)
    demo_error_handling()
    
    # Security features demo
    demo_security_features()
    
    # API features demo
    demo_api_features()
    
    # Monitoring features demo
    demo_monitoring_features()
    
    # Database demo (graceful failure)
    await demo_database()
    
    # Cache demo (graceful failure)
    await demo_cache()
    
    # Service layer demo (graceful failure)
    await demo_services()
    
    print_banner("Demo Complete")
    print("✅ Enterprise FastAPI features demonstrated!")
    print("\n📋 What was shown:")
    print("  • Configuration management and environment handling")
    print("  • Structured logging with JSON output")
    print("  • Custom error handling and validation")
    print("  • Security features (password hashing, JWT)")
    print("  • API models and request/response validation")
    print("  • Prometheus metrics collection")
    print("  • Database connection (with graceful failure)")
    print("  • Redis caching (with graceful failure)")
    print("  • Service layer architecture")
    
    print("\n🚀 Next Steps:")
    print("  1. Run full application: fastapi dev app.main:app")
    print("  2. Visit API docs: http://localhost:8000/docs")
    print("  3. Check health: http://localhost:8000/health")
    print("  4. View metrics: http://localhost:8000/metrics")
    
    print("\n🔧 For full functionality:")
    print("  • Start PostgreSQL: docker compose up -d postgres")
    print("  • Start Redis: docker compose up -d redis")
    
    print("\n📚 Explore individual demos:")
    print("  • Authentication: python examples/demo_authentication.py")
    print("  • WebAuthn: python examples/demo_webauthn.py") 
    print("  • Caching: python examples/demo_caching.py")
    print("  • Rate Limiting: python examples/demo_rate_limiting.py")
    print("  • Metrics: python examples/demo_metrics.py")
    print("  • Health Checks: python examples/demo_health_checks.py")
    print("  • Items API: python examples/demo_items_api.py")
    print("  • Full Overview: python examples/demo_overview.py")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())