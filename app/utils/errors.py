"""
Enterprise-grade error handling and exception management.
Provides consistent error responses and proper exception handling.
"""
import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.models.schemas import ErrorResponse
from app.config import config

logger = logging.getLogger(__name__)


class BusinessLogicError(Exception):
    """Custom exception for business logic errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.field = field
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.operation = operation
        self.details = details or {}
        super().__init__(self.message)


class ExternalServiceError(Exception):
    """Custom exception for external service errors."""
    
    def __init__(self, message: str, service: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.service = service
        self.details = details or {}
        super().__init__(self.message)


async def business_logic_exception_handler(request: Request, exc: BusinessLogicError) -> JSONResponse:
    """Handle business logic exceptions."""
    error_id = str(uuid.uuid4())
    logger.warning(
        f"Business logic error [{error_id}]: {exc.message}",
        extra={"error_id": error_id, "details": exc.details}
    )
    
    error_response = ErrorResponse(
        error="BusinessLogicError",
        message=exc.message,
        details={"error_id": error_id, **exc.details},
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(error_response)
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation exceptions."""
    error_id = str(uuid.uuid4())
    logger.warning(
        f"Validation error [{error_id}]: {exc.message}",
        extra={"error_id": error_id, "field": exc.field, "details": exc.details}
    )
    
    error_response = ErrorResponse(
        error="ValidationError",
        message=exc.message,
        details={"error_id": error_id, "field": exc.field, **exc.details},
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response)
    )


async def database_exception_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle database exceptions."""
    error_id = str(uuid.uuid4())
    logger.error(
        f"Database error [{error_id}]: {exc.message}",
        extra={"error_id": error_id, "operation": exc.operation, "details": exc.details}
    )
    
    # Don't expose internal database details in production
    if config.environment == "production":
        message = "A database error occurred. Please try again later."
        details = {"error_id": error_id}
    else:
        message = exc.message
        details = {"error_id": error_id, "operation": exc.operation, **exc.details}
    
    error_response = ErrorResponse(
        error="DatabaseError",
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response)
    )


async def external_service_exception_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    """Handle external service exceptions."""
    error_id = str(uuid.uuid4())
    logger.error(
        f"External service error [{error_id}]: {exc.message}",
        extra={"error_id": error_id, "service": exc.service, "details": exc.details}
    )
    
    error_response = ErrorResponse(
        error="ExternalServiceError",
        message=f"External service temporarily unavailable: {exc.service}",
        details={"error_id": error_id, "service": exc.service},
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=jsonable_encoder(error_response)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general unhandled exceptions."""
    error_id = str(uuid.uuid4())
    
    # Log the full exception with stack trace
    logger.error(
        f"Unhandled exception [{error_id}]: {str(exc)}",
        extra={"error_id": error_id, "traceback": traceback.format_exc()}
    )
    
    # Don't expose internal error details in production
    if config.environment == "production":
        message = "An unexpected error occurred. Please try again later."
        details = {"error_id": error_id}
    else:
        message = str(exc)
        details = {"error_id": error_id, "type": exc.__class__.__name__}
    
    error_response = ErrorResponse(
        error="InternalServerError",
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    error_id = str(uuid.uuid4())
    
    logger.warning(
        f"HTTP exception [{error_id}]: {exc.detail}",
        extra={"error_id": error_id, "status_code": exc.status_code}
    )
    
    error_response = ErrorResponse(
        error="HTTPError",
        message=exc.detail,
        details={"error_id": error_id, "status_code": exc.status_code},
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response)
    )


def handle_error_with_logging(operation: str):
    """Decorator for handling errors with proper logging."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BusinessLogicError:
                raise  # Re-raise business logic errors as-is
            except ValidationError:
                raise  # Re-raise validation errors as-is
            except Exception as e:
                logger.error(f"Error in {operation}: {str(e)}", exc_info=True)
                raise DatabaseError(f"Database operation failed: {operation}", operation=operation)
        return wrapper
    return decorator