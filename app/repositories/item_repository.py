"""
Repository pattern implementation for data access.
Provides abstraction layer between business logic and data storage.
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.entities import Item, MockItem, _items_storage, get_next_id
from app.models.schemas import (
    ItemCreate,
    ItemUpdate,
    PaginationParams,
    PaginatedResponse,
)
from app.models.database import db_manager

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """Abstract base repository class."""
    
    @abstractmethod
    async def get_by_id(self, id: int):
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, pagination: Optional[PaginationParams] = None):
        """Get all entities with optional pagination."""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]):
        """Create new entity."""
        pass
    
    @abstractmethod
    async def update(self, id: int, data: Dict[str, Any]):
        """Update existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: int):
        """Delete entity by ID."""
        pass


class ItemRepository(BaseRepository):
    """Repository for :class:`Item` entities.

    The original implementation always created its own database session which
    made it impossible to reuse an existing session in calling code.  The test
    suite (and typical repository usage) expects a session to be injectable so
    that multiple operations can share the same transaction.  Without accepting
    a session parameter, instantiating ``ItemRepository`` with a session raised
    ``TypeError``.  This class now accepts an optional SQLAlchemy session and
    uses it for all database operations when provided.
    """

    def __init__(self, session=None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_mock = os.getenv("USE_MOCK_DB", "false").lower() == "true"
        self.session = session
    
    async def get(self, item_id: int) -> Optional[Item]:
        """Alias for :meth:`get_by_id` for backwards compatibility."""
        return await self.get_by_id(item_id)

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Get item by ID with error handling."""
        try:
            self.logger.debug(f"Fetching item with id: {item_id}")

            if self.use_mock:
                # Mock implementation
                item = _items_storage.get(item_id)
                if item:
                    self.logger.debug(f"Found item: {item}")
                else:
                    self.logger.debug(f"Item with id {item_id} not found")
                return item

            if self.session:
                result = await self.session.execute(
                    select(Item).where(Item.id == item_id)
                )
                item = result.scalar_one_or_none()
            else:
                async with db_manager.get_session() as session:
                    result = await session.execute(
                        select(Item).where(Item.id == item_id)
                    )
                    item = result.scalar_one_or_none()

            if item:
                self.logger.debug(f"Found item: {item}")
            else:
                self.logger.debug(f"Item with id {item_id} not found")
            return item

        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching item {item_id}: {e}")
            raise
    
    async def get_all(
        self, pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """Get all items with pagination."""
        try:
            pagination = pagination or PaginationParams()
            self.logger.debug("Fetching all items")

            if self.use_mock:
                # Mock implementation
                all_items = list(_items_storage.values())
                total = len(all_items)

                # Sort by creation time (newest first)
                all_items.sort(key=lambda x: x.created_at, reverse=True)

                start = pagination.offset
                end = start + pagination.limit
                items = all_items[start:end]

                self.logger.debug(f"Found {len(items)} items (total: {total})")
                return PaginatedResponse.create(
                    items=items,
                    total=total,
                    page=pagination.page,
                    limit=pagination.limit,
                )

            if self.session:
                # Get total count
                count_result = await self.session.execute(select(func.count(Item.id)))
                total = count_result.scalar()

                # Get paginated results
                query = select(Item).order_by(Item.created_at.desc())
                query = query.offset(pagination.offset).limit(pagination.limit)
                result = await self.session.execute(query)
                items = result.scalars().all()
            else:
                async with db_manager.get_session() as session:
                    count_result = await session.execute(select(func.count(Item.id)))
                    total = count_result.scalar()

                    query = select(Item).order_by(Item.created_at.desc())
                    query = query.offset(pagination.offset).limit(pagination.limit)

                    result = await session.execute(query)
                    items = result.scalars().all()

            self.logger.debug(f"Found {len(items)} items (total: {total})")
            return PaginatedResponse.create(
                items=list(items),
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            )

        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching items: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching items: {e}")
            raise
    
    async def create(self, item_data: ItemCreate) -> Item:
        """Create new item with validation."""
        try:
            self.logger.debug(f"Creating new item: {item_data.model_dump()}")
            
            if self.use_mock:
                # Mock implementation
                item_id = get_next_id()
                item = MockItem(
                    id=item_id,
                    name=item_data.name,
                    price=item_data.price,
                    is_offer=item_data.is_offer,
                )
                _items_storage[item_id] = item

                self.logger.info(f"Created item with id: {item_id}")
                return item

            if self.session:
                db_item = Item(**item_data.model_dump())
                self.session.add(db_item)
                await self.session.commit()
                await self.session.refresh(db_item)
                self.logger.info(f"Created item with id: {db_item.id}")
                return db_item
            else:
                async with db_manager.get_session() as session:
                    db_item = Item(**item_data.model_dump())
                    session.add(db_item)
                    await session.commit()
                    await session.refresh(db_item)

                    self.logger.info(f"Created item with id: {db_item.id}")
                    return db_item
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating item: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating item: {e}")
            raise
    
    async def update(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        """Update existing item."""
        try:
            self.logger.debug(f"Updating item {item_id}: {item_data.model_dump(exclude_unset=True)}")
            
            if self.use_mock:
                # Mock implementation
                item = _items_storage.get(item_id)
                if not item:
                    self.logger.debug(f"Item {item_id} not found for update")
                    return None

                update_data = item_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(item, field, value)

                item.updated_at = datetime.now()

                self.logger.info(f"Updated item {item_id}")
                return item

            if self.session:
                result = await self.session.execute(
                    select(Item).where(Item.id == item_id)
                )
                db_item = result.scalar_one_or_none()
                if not db_item:
                    self.logger.debug(f"Item {item_id} not found for update")
                    return None

                update_data = item_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(db_item, field, value)

                db_item.updated_at = func.now()
                await self.session.commit()
                await self.session.refresh(db_item)
                self.logger.info(f"Updated item {item_id}")
                return db_item
            else:
                async with db_manager.get_session() as session:
                    result = await session.execute(
                        select(Item).where(Item.id == item_id)
                    )
                    db_item = result.scalar_one_or_none()

                    if not db_item:
                        self.logger.debug(f"Item {item_id} not found for update")
                        return None

                    update_data = item_data.model_dump(exclude_unset=True)
                    for field, value in update_data.items():
                        setattr(db_item, field, value)

                    db_item.updated_at = func.now()
                    await session.commit()
                    await session.refresh(db_item)

                    self.logger.info(f"Updated item {item_id}")
                    return db_item
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating item {item_id}: {e}")
            raise
    
    async def delete(self, item_id: int) -> bool:
        """Delete item by ID."""
        try:
            self.logger.debug(f"Deleting item: {item_id}")
            
            if self.use_mock:
                # Mock implementation
                if item_id in _items_storage:
                    del _items_storage[item_id]
                    self.logger.info(f"Deleted item {item_id}")
                    return True
                else:
                    self.logger.debug(f"Item {item_id} not found for deletion")
                    return False

            if self.session:
                result = await self.session.execute(
                    select(Item).where(Item.id == item_id)
                )
                db_item = result.scalar_one_or_none()
                if not db_item:
                    self.logger.debug(f"Item {item_id} not found for deletion")
                    return False

                await self.session.delete(db_item)
                await self.session.commit()
                self.logger.info(f"Deleted item {item_id}")
                return True
            else:
                async with db_manager.get_session() as session:
                    result = await session.execute(
                        select(Item).where(Item.id == item_id)
                    )
                    db_item = result.scalar_one_or_none()

                    if not db_item:
                        self.logger.debug(f"Item {item_id} not found for deletion")
                        return False

                    await session.delete(db_item)
                    await session.commit()

                    self.logger.info(f"Deleted item {item_id}")
                    return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting item {item_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting item {item_id}: {e}")
            raise
    
    async def search(
        self, query: str, pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """Search items by name."""
        try:
            pagination = pagination or PaginationParams()
            self.logger.debug(f"Searching items with query: {query}")

            if self.use_mock:
                # Mock implementation
                all_items = list(_items_storage.values())
                filtered_items = [
                    item for item in all_items if query.lower() in item.name.lower()
                ]

                total = len(filtered_items)

                # Sort by relevance and creation time
                filtered_items.sort(key=lambda x: x.created_at, reverse=True)

                start = pagination.offset
                end = start + pagination.limit
                items = filtered_items[start:end]

                self.logger.debug(
                    f"Found {len(items)} items matching query (total: {total})"
                )
                return PaginatedResponse.create(
                    items=items,
                    total=total,
                    page=pagination.page,
                    limit=pagination.limit,
                )

            search_query = f"%{query.lower()}%"
            if self.session:
                count_result = await self.session.execute(
                    select(func.count(Item.id)).where(
                        func.lower(Item.name).like(search_query)
                    )
                )
                total = count_result.scalar()

                query_stmt = (
                    select(Item)
                    .where(func.lower(Item.name).like(search_query))
                    .order_by(Item.created_at.desc())
                    .offset(pagination.offset)
                    .limit(pagination.limit)
                )
                result = await self.session.execute(query_stmt)
                items = result.scalars().all()
            else:
                async with db_manager.get_session() as session:
                    count_result = await session.execute(
                        select(func.count(Item.id)).where(
                            func.lower(Item.name).like(search_query)
                        )
                    )
                    total = count_result.scalar()

                    query_stmt = (
                        select(Item)
                        .where(func.lower(Item.name).like(search_query))
                        .order_by(Item.created_at.desc())
                        .offset(pagination.offset)
                        .limit(pagination.limit)
                    )
                    result = await session.execute(query_stmt)
                    items = result.scalars().all()

            self.logger.debug(f"Found {len(items)} items matching query (total: {total})")
            return PaginatedResponse.create(
                items=list(items),
                total=total,
                page=pagination.page,
                limit=pagination.limit,
            )

        except SQLAlchemyError as e:
            self.logger.error(f"Database error searching items: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error searching items: {e}")
            raise
