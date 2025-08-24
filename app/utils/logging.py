"""
Enterprise-grade logging configuration.
Provides structured logging with proper formatting and levels.
"""
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from app.config import config


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        
        # Convert to JSON string manually to avoid import issues
        import json
        return json.dumps(log_obj)


def setup_logging() -> None:
    """Setup application logging configuration."""
    
    # Create formatters
    if config.logging.format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        handlers=[console_handler],
        force=True
    )
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # Set our application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, config.logging.level.upper()))
    
    logging.info("Logging configuration initialized")


def get_logger(name: str) -> logging.Logger:
    """Get logger with proper configuration."""
    return logging.getLogger(f"app.{name}")


class RequestLogger:
    """Request-specific logger with request ID tracking."""
    
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with request ID."""
        extra = {"request_id": self.request_id, **kwargs}
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with request ID."""
        extra = {"request_id": self.request_id, **kwargs}
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with request ID."""
        extra = {"request_id": self.request_id, **kwargs}
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with request ID."""
        extra = {"request_id": self.request_id, **kwargs}
        self.logger.error(message, extra=extra)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with request ID."""
        extra = {"request_id": self.request_id, **kwargs}
        self.logger.critical(message, extra=extra)