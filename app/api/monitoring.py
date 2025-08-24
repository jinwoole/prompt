"""Monitoring and metrics API endpoints."""
from fastapi import APIRouter, Response
from app.monitoring import get_metrics, get_metrics_content_type

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for scraping.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


@router.get("/health/detailed")
async def detailed_health():
    """
    Detailed health check with component status.
    
    Returns detailed status of all application components.
    """
    from app.models.database import get_engine
    from app.cache.redis_client import get_redis
    from app.config import config
    import asyncio
    
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T10:00:00Z",
        "version": config.version,
        "environment": config.environment,
        "components": {}
    }
    
    # Check database
    try:
        engine = get_engine()
        if engine:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        else:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": "Database engine not initialized"
            }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
    
    # Check Redis cache
    try:
        redis_client = get_redis()
        if redis_client:
            await redis_client.ping()
            health_status["components"]["cache"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        else:
            health_status["components"]["cache"] = {
                "status": "degraded",
                "message": "Redis not configured or unavailable"
            }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
    
    # Determine overall status
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["status"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the application is ready to serve traffic.
    """
    from app.models.database import get_engine
    
    # Check if database is accessible
    try:
        engine = get_engine()
        if engine:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            return {"status": "ready"}
        else:
            return {"status": "not ready", "reason": "database not initialized"}
    except Exception as e:
        return {"status": "not ready", "reason": f"database error: {str(e)}"}