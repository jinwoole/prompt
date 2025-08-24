"""
Enterprise FastAPI Application with PostgreSQL integration.

This is the main application module that initializes and configures
the FastAPI application with enterprise-grade features:
- Database connection management
- Structured logging
- Error handling
- CORS configuration
- Health checks
- Graceful shutdown
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import config
from app.models.database import init_database, close_database
from app.cache.redis_client import init_redis, close_redis
from app.api.items import router as items_router
from app.api.auth import router as auth_router
from app.api.passkey import router as passkey_router
from app.api.monitoring import router as monitoring_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.monitoring import MetricsMiddleware
from app.utils.logging import setup_logging
from app.utils.errors import (
    BusinessLogicError, ValidationError, DatabaseError, ExternalServiceError,
    business_logic_exception_handler, validation_exception_handler,
    database_exception_handler, external_service_exception_handler,
    general_exception_handler, http_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events with proper resource management.
    """
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("Starting application...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize Redis cache
        await init_redis()
        logger.info("Cache initialized successfully")
        
        # Add any other startup tasks here
        logger.info("Application startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        try:
            # Close database connections
            await close_database()
            logger.info("Database connections closed")
            
            # Close Redis connections
            await close_redis()
            logger.info("Cache connections closed")
            
            # Add any other cleanup tasks here
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Creating application in {config.environment} environment")
    
    # Create FastAPI application
    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        debug=config.debug,
        lifespan=lifespan,
        docs_url="/docs" if config.environment != "production" else None,
        redoc_url="/redoc" if config.environment != "production" else None,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.cors_origins,
        allow_credentials=True,
        allow_methods=config.security.cors_methods,
        allow_headers=config.security.cors_headers,
    )
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add exception handlers
    app.add_exception_handler(BusinessLogicError, business_logic_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(DatabaseError, database_exception_handler)
    app.add_exception_handler(ExternalServiceError, external_service_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Add middleware for request logging and tracking
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """Log requests and add request ID tracking."""
        import uuid
        import time
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log successful response
            duration = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error response
            duration = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            raise
    
    # Include routers
    app.include_router(auth_router)
    app.include_router(passkey_router)
    app.include_router(items_router)
    app.include_router(monitoring_router)
    
    # Root endpoint
    @app.get("/", summary="Root Endpoint")
    async def read_root():
        """
        Root endpoint providing basic application information.
        """
        return {
            "message": "Enterprise FastAPI Application",
            "version": config.version,
            "environment": config.environment,
            "docs_url": "/docs" if config.environment != "production" else None
        }
    
    logger.info("Application created successfully")
    return app


# Create the application instance
app = create_application()