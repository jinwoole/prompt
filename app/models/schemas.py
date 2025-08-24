"""
Pydantic models for API request/response validation.
Provides type-safe data models with validation.
"""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, validator


class ItemBase(BaseModel):
    """Base item model with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    price: float = Field(..., ge=0, description="Item price (must be non-negative)")
    is_offer: Optional[bool] = Field(default=None, description="Whether item is on offer")


class ItemCreate(ItemBase):
    """Model for creating new items."""
    pass


class ItemUpdate(ItemBase):
    """Model for updating existing items."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0)


class Item(ItemBase):
    """Complete item model with database fields."""
    id: int = Field(..., description="Unique item identifier")
    created_at: datetime = Field(..., description="Item creation timestamp")
    updated_at: datetime = Field(..., description="Item last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database: bool = Field(..., description="Database connection status")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(10, ge=1, le=100, description="Items per page (max 100)")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: list = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(cls, items: list, total: int, page: int, limit: int):
        """Create paginated response."""
        pages = (total + limit - 1) // limit  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )