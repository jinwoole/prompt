"""
Database connection and session management.
Provides async database connection with proper connection pooling and error handling.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import event, text
import asyncpg

from app.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    Provides connection pooling, health checks, and proper cleanup.
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._is_connected = False
    
    async def initialize(self) -> None:
        """Initialize database connection and create engine."""
        try:
            logger.info("Initializing database connection...")
            
            # Check if we should use mock database (for testing without PostgreSQL)
            use_mock = os.getenv("USE_MOCK_DB", "false").lower() == "true"
            
            if use_mock:
                logger.info("Using mock database implementation")
                self._is_connected = True
                return
            
            # Real PostgreSQL connection
            self.engine = create_async_engine(
                config.database.url,
                pool_size=config.database.pool_size,
                max_overflow=config.database.max_overflow,
                pool_timeout=config.database.pool_timeout,
                pool_recycle=config.database.pool_recycle,
                echo=config.debug,
                future=True,
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Test the connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info(f"Database connection initialized successfully")
            logger.info(f"Database URL: {config.database.url}")
            self._is_connected = True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self._is_connected = False
            raise
    
    async def close(self) -> None:
        """Close database connections and cleanup."""
        if self.engine:
            logger.info("Closing database connections...")
            await self.engine.dispose()
            self._is_connected = False
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            # Check if using mock database
            use_mock = os.getenv("USE_MOCK_DB", "false").lower() == "true"
            if use_mock:
                return self._is_connected
            
            # Real database health check
            if not self.session_factory:
                return False
                
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator:
        """Get async database session with proper error handling."""
        # Check if using mock database
        use_mock = os.getenv("USE_MOCK_DB", "false").lower() == "true"
        if use_mock:
            # Mock session for testing
            class MockSession:
                async def commit(self): pass
                async def rollback(self): pass
                async def close(self): pass
            yield MockSession()
            return
        
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        # Real database session
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session():
    """Dependency to get database session."""
    async with db_manager.get_session() as session:
        yield session


async def init_database():
    """Initialize database on application startup."""
    await db_manager.initialize()


async def close_database():
    """Close database connections on application shutdown."""
    await db_manager.close()


def get_engine():
    """Get the database engine."""
    return db_manager.engine