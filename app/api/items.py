"""
Item management API endpoints with enterprise-grade features.
Provides RESTful API with proper error handling, validation, and documentation.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.models.schemas import (
    Item, ItemCreate, ItemUpdate, HealthCheck, 
    PaginationParams, PaginatedResponse, ErrorResponse
)
from app.services.item_service import ItemService
from app.repositories.item_repository import ItemRepository
from app.models.database import db_manager
from app.utils.errors import BusinessLogicError, ValidationError
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["items"])

# Dependency injection
def get_item_service() -> ItemService:
    """Get item service instance with proper dependency injection."""
    item_repository = ItemRepository()
    return ItemService(item_repository)


@router.get("/health", response_model=HealthCheck, summary="Health Check")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns the current status of the application and its dependencies.
    """
    try:
        # Check database connection
        db_healthy = await db_manager.health_check()
        
        health_status = HealthCheck(
            status="healthy" if db_healthy else "degraded",
            timestamp=datetime.now(timezone.utc),
            database=db_healthy,
            version=config.version
        )
        
        status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(health_status)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_health = HealthCheck(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc),
            database=False,
            version=config.version
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(error_health)
        )


@router.get("/items", response_model=PaginatedResponse, summary="Get Items")
async def get_items(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    service: ItemService = Depends(get_item_service)
):
    """
    Get all items with pagination.
    
    - **page**: Page number (starts from 1)
    - **limit**: Number of items per page (maximum 100)
    
    Returns paginated list of items with metadata.
    """
    try:
        pagination = PaginationParams(page=page, limit=limit)
        result = await service.get_items(pagination)
        
        logger.info(f"Retrieved {len(result.items)} items (page {page}, limit {limit})")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve items"
        )


@router.get("/items/search", response_model=PaginatedResponse, summary="Search Items")
async def search_items(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    service: ItemService = Depends(get_item_service)
):
    """
    Search items by name.
    
    - **q**: Search query (minimum 2 characters)
    - **page**: Page number (starts from 1)
    - **limit**: Number of items per page (maximum 100)
    
    Returns paginated list of items matching the search query.
    """
    try:
        pagination = PaginationParams(page=page, limit=limit)
        result = await service.search_items(q, pagination)
        
        logger.info(f"Search for '{q}' returned {len(result.items)} items")
        return result
        
    except Exception as e:
        logger.error(f"Error searching items with query '{q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search items"
        )


@router.get("/items/{item_id}", response_model=Item, summary="Get Item by ID")
async def get_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    """
    Get a specific item by ID.
    
    - **item_id**: Unique identifier of the item
    
    Returns the item details if found.
    """
    try:
        item = await service.get_item(item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        logger.info(f"Retrieved item {item_id}")
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve item"
        )


@router.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED, summary="Create Item")
async def create_item(
    item_data: ItemCreate,
    service: ItemService = Depends(get_item_service)
):
    """
    Create a new item.
    
    - **name**: Item name (required, 1-100 characters)
    - **price**: Item price (required, must be non-negative)
    - **is_offer**: Whether the item is on offer (optional)
    
    Returns the created item with assigned ID and timestamps.
    """
    try:
        item = await service.create_item(item_data)
        
        logger.info(f"Created item {item.id}: {item.name}")
        return item
        
    except Exception as e:
        logger.error(f"Error creating item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )


@router.put("/items/{item_id}", response_model=Item, summary="Update Item")
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    service: ItemService = Depends(get_item_service)
):
    """
    Update an existing item.
    
    - **item_id**: Unique identifier of the item to update
    - **name**: New item name (optional, 1-100 characters)
    - **price**: New item price (optional, must be non-negative)
    - **is_offer**: New offer status (optional)
    
    Returns the updated item with new timestamps.
    """
    try:
        item = await service.update_item(item_id, item_data)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        logger.info(f"Updated item {item_id}")
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item"
        )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Item")
async def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    """
    Delete an item by ID.
    
    - **item_id**: Unique identifier of the item to delete
    
    Returns 204 No Content on successful deletion.
    """
    try:
        success = await service.delete_item(item_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        logger.info(f"Deleted item {item_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )
