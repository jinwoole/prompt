"""
Configuration management for the FastAPI application.
Provides environment-based configuration with validation and type safety.
"""
import os
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 5432
    database: str = "fastapi_db"
    username: str = "postgres"
    password: str = "password"
    
    # Connection pool settings for production
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @property
    def url(self) -> str:
        """Generate database URL."""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def sync_url(self) -> str:
        """Generate synchronous database URL for migrations."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "json"  # json or text
    include_request_id: bool = True


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    
    # Cache TTL settings (in seconds)
    default_ttl: int = 300  # 5 minutes
    short_ttl: int = 60     # 1 minute
    long_ttl: int = 3600    # 1 hour


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    cors_origins: list[str] = ["*"]
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: list[str] = ["*"]
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # JWT settings
    secret_key: str = "your-secret-key-here-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Passkey/WebAuthn settings
    passkey_rp_id: str = "localhost"
    passkey_rp_name: str = "Enterprise FastAPI Application"
    passkey_challenge_timeout: int = 300  # seconds


class AppConfig(BaseModel):
    """Main application configuration."""
    title: str = "Enterprise FastAPI Application"
    description: str = "A production-ready FastAPI application with PostgreSQL"
    version: str = "1.0.0"
    debug: bool = False
    
    # Environment
    environment: str = "development"
    
    # Database configuration
    database: DatabaseConfig = DatabaseConfig()
    
    # Cache configuration
    cache: CacheConfig = CacheConfig()
    
    # Logging configuration
    logging: LoggingConfig = LoggingConfig()
    
    # Security configuration
    security: SecurityConfig = SecurityConfig()
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    model_config = ConfigDict(env_nested_delimiter="__")


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    
    # Database configuration from environment
    db_config = DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "fastapi_db"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "30")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
    )
    
    # Cache configuration
    cache_config = CacheConfig(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        socket_connect_timeout=int(os.getenv("REDIS_CONNECT_TIMEOUT", "5")),
        socket_timeout=int(os.getenv("REDIS_TIMEOUT", "5")),
        default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),
        short_ttl=int(os.getenv("CACHE_SHORT_TTL", "60")),
        long_ttl=int(os.getenv("CACHE_LONG_TTL", "3600")),
    )
    
    # Logging configuration
    logging_config = LoggingConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=os.getenv("LOG_FORMAT", "json"),
        include_request_id=os.getenv("LOG_INCLUDE_REQUEST_ID", "true").lower() == "true",
    )
    
    # Security configuration
    security_config = SecurityConfig(
        cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        cors_methods=os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE").split(","),
        cors_headers=os.getenv("CORS_HEADERS", "*").split(","),
        rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        secret_key=os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        passkey_rp_id=os.getenv("PASSKEY_RP_ID", "localhost"),
        passkey_rp_name=os.getenv("PASSKEY_RP_NAME", "Enterprise FastAPI Application"),
        passkey_challenge_timeout=int(os.getenv("PASSKEY_CHALLENGE_TIMEOUT", "300")),
    )
    
    # Main app configuration
    config = AppConfig(
        title=os.getenv("APP_TITLE", "Enterprise FastAPI Application"),
        description=os.getenv("APP_DESCRIPTION", "A production-ready FastAPI application with PostgreSQL"),
        version=os.getenv("APP_VERSION", "1.0.0"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "development"),
        database=db_config,
        cache=cache_config,
        logging=logging_config,
        security=security_config,
    )
    
    return config


# Global configuration instance
config = load_config()