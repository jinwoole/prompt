"""
Business logic layer for item management.
Implements enterprise-grade business rules and validation.
"""
import logging
from typing import List, Optional
from datetime import datetime

from app.models.schemas import Item, ItemCreate, ItemUpdate, PaginationParams, PaginatedResponse
from app.repositories.item_repository import ItemRepository

logger = logging.getLogger(__name__)


class ItemService:
    """Service class for item business logic with enterprise-grade error handling."""
    
    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get_item(self, item_id: int) -> Optional[Item]:
        """Get item by ID with business logic validation."""
        try:
            self.logger.debug(f"Service: Getting item {item_id}")
            
            if item_id <= 0:
                self.logger.warning(f"Invalid item ID provided: {item_id}")
                return None
            
            db_item = await self.item_repository.get_by_id(item_id)
            
            if db_item:
                # Convert database model to Pydantic model
                return Item(
                    id=db_item.id,
                    name=db_item.name,
                    price=db_item.price,
                    is_offer=db_item.is_offer,
                    created_at=db_item.created_at,
                    updated_at=db_item.updated_at
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Service error getting item {item_id}: {e}")
            raise
    
    async def get_items(self, pagination: Optional[PaginationParams] = None) -> PaginatedResponse:
        """Get all items with pagination and business logic."""
        try:
            self.logger.debug("Service: Getting all items")
            
            # Set default pagination if not provided
            if pagination is None:
                pagination = PaginationParams()
            
            db_response = await self.item_repository.get_all(pagination)

            # Convert database models to Pydantic models
            items = [
                Item(
                    id=db_item.id,
                    name=db_item.name,
                    price=db_item.price,
                    is_offer=db_item.is_offer,
                    created_at=db_item.created_at,
                    updated_at=db_item.updated_at,
                )
                for db_item in db_response.items
            ]

            return PaginatedResponse.create(
                items=items,
                total=db_response.total,
                page=db_response.page,
                limit=db_response.limit,
            )
            
        except Exception as e:
            self.logger.error(f"Service error getting items: {e}")
            raise
    
    async def create_item(self, item_data: ItemCreate) -> Item:
        """Create new item with business validation."""
        try:
            self.logger.debug(f"Service: Creating item {item_data.model_dump()}")
            
            # Business rule validation
            await self._validate_item_data(item_data)
            
            # Check for duplicate names (business rule)
            if await self._is_name_duplicate(item_data.name):
                from app.utils.errors import BusinessLogicError
                raise BusinessLogicError(f"Item with name '{item_data.name}' already exists")
            
            db_item = await self.item_repository.create(item_data)
            
            # Convert to Pydantic model
            item = Item(
                id=db_item.id,
                name=db_item.name,
                price=db_item.price,
                is_offer=db_item.is_offer,
                created_at=db_item.created_at,
                updated_at=db_item.updated_at
            )
            
            self.logger.info(f"Service: Created item {item.id}")
            return item
            
        except Exception as e:
            self.logger.error(f"Service error creating item: {e}")
            raise
    
    async def update_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        """Update item with business validation."""
        try:
            self.logger.debug(f"Service: Updating item {item_id}")
            
            if item_id <= 0:
                self.logger.warning(f"Invalid item ID for update: {item_id}")
                return None
            
            # Validate update data
            await self._validate_item_update_data(item_data)
            
            # Check for duplicate names if name is being updated
            if item_data.name and await self._is_name_duplicate(item_data.name, exclude_id=item_id):
                from app.utils.errors import BusinessLogicError
                raise BusinessLogicError(f"Item with name '{item_data.name}' already exists")
            
            db_item = await self.item_repository.update(item_id, item_data)
            
            if db_item:
                item = Item(
                    id=db_item.id,
                    name=db_item.name,
                    price=db_item.price,
                    is_offer=db_item.is_offer,
                    created_at=db_item.created_at,
                    updated_at=db_item.updated_at
                )
                
                self.logger.info(f"Service: Updated item {item.id}")
                return item
            
            return None
            
        except Exception as e:
            self.logger.error(f"Service error updating item {item_id}: {e}")
            raise
    
    async def delete_item(self, item_id: int) -> bool:
        """Delete item with business logic checks."""
        try:
            self.logger.debug(f"Service: Deleting item {item_id}")
            
            if item_id <= 0:
                self.logger.warning(f"Invalid item ID for deletion: {item_id}")
                return False
            
            # Business rule: Check if item can be deleted
            if not await self._can_delete_item(item_id):
                self.logger.warning(f"Item {item_id} cannot be deleted due to business rules")
                return False
            
            success = await self.item_repository.delete(item_id)
            
            if success:
                self.logger.info(f"Service: Deleted item {item_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Service error deleting item {item_id}: {e}")
            raise
    
    async def search_items(self, query: str, pagination: Optional[PaginationParams] = None) -> PaginatedResponse:
        """Search items with business logic."""
        try:
            self.logger.debug(f"Service: Searching items with query: {query}")
            
            if not query or len(query.strip()) < 2:
                self.logger.warning("Search query too short")
                return PaginatedResponse.create(items=[], total=0, page=1, limit=10)
            
            # Set default pagination if not provided
            if pagination is None:
                pagination = PaginationParams()
            
            db_response = await self.item_repository.search(query.strip(), pagination)

            # Convert database models to Pydantic models
            items = [
                Item(
                    id=db_item.id,
                    name=db_item.name,
                    price=db_item.price,
                    is_offer=db_item.is_offer,
                    created_at=db_item.created_at,
                    updated_at=db_item.updated_at,
                )
                for db_item in db_response.items
            ]

            return PaginatedResponse.create(
                items=items,
                total=db_response.total,
                page=db_response.page,
                limit=db_response.limit,
            )
            
        except Exception as e:
            self.logger.error(f"Service error searching items: {e}")
            raise
    
    async def _validate_item_data(self, item_data: ItemCreate) -> None:
        """Validate item data according to business rules."""
        from app.utils.errors import BusinessLogicError
        
        # Business rule: Price must be reasonable
        if item_data.price > 1000000:
            raise BusinessLogicError("Price cannot exceed $1,000,000")
        
        # Business rule: Name must not contain prohibited words
        prohibited_words = ["spam", "scam", "fake"]
        if any(word in item_data.name.lower() for word in prohibited_words):
            raise BusinessLogicError("Item name contains prohibited content")
    
    async def _validate_item_update_data(self, item_data: ItemUpdate) -> None:
        """Validate item update data according to business rules."""
        from app.utils.errors import BusinessLogicError
        
        if item_data.price is not None and item_data.price > 1000000:
            raise BusinessLogicError("Price cannot exceed $1,000,000")
        
        if item_data.name is not None:
            prohibited_words = ["spam", "scam", "fake"]
            if any(word in item_data.name.lower() for word in prohibited_words):
                raise BusinessLogicError("Item name contains prohibited content")
    
    async def _is_name_duplicate(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if item name already exists."""
        # In a real implementation, this would be a database query
        # For mock implementation, we'll check the in-memory storage
        from app.models.entities import _items_storage
        
        for item_id, item in _items_storage.items():
            if exclude_id and item_id == exclude_id:
                continue
            if item.name.lower() == name.lower():
                return True
        
        return False
    
    async def _can_delete_item(self, item_id: int) -> bool:
        """Check if item can be deleted according to business rules."""
        # Business rule: Items with certain conditions might not be deletable
        # For example, items that are part of active orders
        # This is a placeholder for actual business logic
        return True
