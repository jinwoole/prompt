#!/usr/bin/env python3
"""
Demo script showcasing Items API functionality.

This demo demonstrates:
- CRUD operations (Create, Read, Update, Delete)
- Search and filtering capabilities
- Pagination with proper limits
- Data validation and error handling
- Business logic validation
- API response models
- Query optimization patterns
"""
import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


@dataclass
class Item:
    """Item data model."""
    id: int
    name: str
    price: float
    is_offer: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class ItemCreate:
    """Item creation model."""
    name: str
    price: float
    is_offer: bool = False


@dataclass
class ItemUpdate:
    """Item update model."""
    name: Optional[str] = None
    price: Optional[float] = None
    is_offer: Optional[bool] = None


@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    limit: int = 10
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


@dataclass
class PaginatedResponse:
    """Paginated response wrapper."""
    items: List[Item]
    total: int
    page: int
    limit: int
    pages: int
    
    @classmethod
    def create(cls, items: List[Item], total: int, page: int, limit: int):
        pages = (total + limit - 1) // limit
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)


class ValidationError(Exception):
    """Validation error for business rules."""
    pass


class ItemService:
    """Item service with business logic."""
    
    def __init__(self):
        self.items: Dict[int, Item] = {}
        self.next_id = 1
    
    def _validate_item_create(self, item_data: ItemCreate):
        """Validate item creation data."""
        if not item_data.name or len(item_data.name.strip()) == 0:
            raise ValidationError("Item name cannot be empty")
        
        if len(item_data.name) > 100:
            raise ValidationError("Item name cannot exceed 100 characters")
        
        if item_data.price < 0:
            raise ValidationError("Item price cannot be negative")
        
        if item_data.price > 999999.99:
            raise ValidationError("Item price cannot exceed $999,999.99")
        
        # Business rule: prevent spam products
        spam_keywords = ["spam", "test", "dummy", "fake"]
        if any(keyword in item_data.name.lower() for keyword in spam_keywords):
            raise ValidationError("Item name contains prohibited content")
    
    def _validate_item_update(self, item_id: int, item_data: ItemUpdate):
        """Validate item update data."""
        if item_id not in self.items:
            raise ValidationError(f"Item with ID {item_id} not found")
        
        if item_data.name is not None:
            if not item_data.name or len(item_data.name.strip()) == 0:
                raise ValidationError("Item name cannot be empty")
            if len(item_data.name) > 100:
                raise ValidationError("Item name cannot exceed 100 characters")
        
        if item_data.price is not None:
            if item_data.price < 0:
                raise ValidationError("Item price cannot be negative")
            if item_data.price > 999999.99:
                raise ValidationError("Item price cannot exceed $999,999.99")
    
    async def create_item(self, item_data: ItemCreate) -> Item:
        """Create a new item."""
        self._validate_item_create(item_data)
        
        now = datetime.now(timezone.utc)
        item = Item(
            id=self.next_id,
            name=item_data.name.strip(),
            price=round(item_data.price, 2),
            is_offer=item_data.is_offer,
            created_at=now,
            updated_at=now
        )
        
        self.items[self.next_id] = item
        self.next_id += 1
        
        return item
    
    async def get_item(self, item_id: int) -> Optional[Item]:
        """Get item by ID."""
        return self.items.get(item_id)
    
    async def get_items(self, pagination: PaginationParams) -> PaginatedResponse:
        """Get paginated list of items."""
        all_items = list(self.items.values())
        total = len(all_items)
        
        # Apply pagination
        start_idx = pagination.offset
        end_idx = start_idx + pagination.limit
        paginated_items = all_items[start_idx:end_idx]
        
        return PaginatedResponse.create(
            items=paginated_items,
            total=total,
            page=pagination.page,
            limit=pagination.limit
        )
    
    async def search_items(self, query: str, pagination: PaginationParams) -> PaginatedResponse:
        """Search items by name."""
        query_lower = query.lower().strip()
        
        # Filter items that match the search query
        matching_items = [
            item for item in self.items.values()
            if query_lower in item.name.lower()
        ]
        
        total = len(matching_items)
        
        # Apply pagination to filtered results
        start_idx = pagination.offset
        end_idx = start_idx + pagination.limit
        paginated_items = matching_items[start_idx:end_idx]
        
        return PaginatedResponse.create(
            items=paginated_items,
            total=total,
            page=pagination.page,
            limit=pagination.limit
        )
    
    async def filter_items(self, filters: Dict[str, Any], pagination: PaginationParams) -> PaginatedResponse:
        """Filter items by various criteria."""
        filtered_items = list(self.items.values())
        
        # Apply filters
        if "min_price" in filters:
            filtered_items = [item for item in filtered_items if item.price >= filters["min_price"]]
        
        if "max_price" in filters:
            filtered_items = [item for item in filtered_items if item.price <= filters["max_price"]]
        
        if "is_offer" in filters:
            filtered_items = [item for item in filtered_items if item.is_offer == filters["is_offer"]]
        
        if "name_contains" in filters:
            search_term = filters["name_contains"].lower()
            filtered_items = [item for item in filtered_items if search_term in item.name.lower()]
        
        total = len(filtered_items)
        
        # Apply pagination
        start_idx = pagination.offset
        end_idx = start_idx + pagination.limit
        paginated_items = filtered_items[start_idx:end_idx]
        
        return PaginatedResponse.create(
            items=paginated_items,
            total=total,
            page=pagination.page,
            limit=pagination.limit
        )
    
    async def update_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        """Update an existing item."""
        self._validate_item_update(item_id, item_data)
        
        if item_id not in self.items:
            return None
        
        item = self.items[item_id]
        
        # Update fields that are provided
        if item_data.name is not None:
            item.name = item_data.name.strip()
        
        if item_data.price is not None:
            item.price = round(item_data.price, 2)
        
        if item_data.is_offer is not None:
            item.is_offer = item_data.is_offer
        
        item.updated_at = datetime.now(timezone.utc)
        
        return item
    
    async def delete_item(self, item_id: int) -> bool:
        """Delete an item."""
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get item statistics."""
        if not self.items:
            return {
                "total_items": 0,
                "average_price": 0,
                "min_price": 0,
                "max_price": 0,
                "offers_count": 0,
                "offers_percentage": 0
            }
        
        prices = [item.price for item in self.items.values()]
        offers = [item for item in self.items.values() if item.is_offer]
        
        return {
            "total_items": len(self.items),
            "average_price": round(sum(prices) / len(prices), 2),
            "min_price": min(prices),
            "max_price": max(prices),
            "offers_count": len(offers),
            "offers_percentage": round((len(offers) / len(self.items)) * 100, 1)
        }


async def demo_crud_operations():
    """Demonstrate CRUD operations."""
    print_banner("CRUD Operations Demo")
    
    service = ItemService()
    
    print("✓ Create operations:")
    
    # Create sample items
    sample_items = [
        ItemCreate(name="MacBook Pro 16\"", price=2499.99, is_offer=False),
        ItemCreate(name="Wireless Mouse", price=29.99, is_offer=True),
        ItemCreate(name="Mechanical Keyboard", price=149.99, is_offer=False),
        ItemCreate(name="4K Monitor", price=599.99, is_offer=True),
        ItemCreate(name="USB-C Cable", price=19.99, is_offer=False),
    ]
    
    created_items = []
    for item_data in sample_items:
        try:
            item = await service.create_item(item_data)
            created_items.append(item)
            offer_flag = " (ON OFFER)" if item.is_offer else ""
            print(f"  ✓ Created: {item.name} - ${item.price}{offer_flag}")
        except ValidationError as e:
            print(f"  ✗ Failed to create {item_data.name}: {e}")
    
    print(f"\n✓ Read operations:")
    
    # Read individual items
    for item in created_items[:3]:  # Show first 3
        retrieved_item = await service.get_item(item.id)
        if retrieved_item:
            print(f"  ✓ Retrieved ID {item.id}: {retrieved_item.name}")
        else:
            print(f"  ✗ Item ID {item.id} not found")
    
    # Try to read non-existent item
    missing_item = await service.get_item(999)
    print(f"  ✓ Non-existent item (ID 999): {missing_item}")
    
    print(f"\n✓ Update operations:")
    
    # Update operations
    if created_items:
        first_item = created_items[0]
        
        # Update price
        update_data = ItemUpdate(price=2299.99, is_offer=True)
        updated_item = await service.update_item(first_item.id, update_data)
        if updated_item:
            print(f"  ✓ Updated price: {updated_item.name} -> ${updated_item.price} (now on offer)")
        
        # Update name
        second_item = created_items[1]
        update_data = ItemUpdate(name="Wireless Gaming Mouse")
        updated_item = await service.update_item(second_item.id, update_data)
        if updated_item:
            print(f"  ✓ Updated name: ID {second_item.id} -> {updated_item.name}")
    
    print(f"\n✓ Delete operations:")
    
    # Delete operations
    if len(created_items) >= 2:
        item_to_delete = created_items[-1]  # Delete last item
        success = await service.delete_item(item_to_delete.id)
        print(f"  ✓ Deleted: {item_to_delete.name} -> {'Success' if success else 'Failed'}")
        
        # Try to delete non-existent item
        success = await service.delete_item(999)
        print(f"  ✓ Delete non-existent (ID 999): {'Success' if success else 'Failed (expected)'}")


async def demo_search_and_filtering():
    """Demonstrate search and filtering capabilities."""
    print_banner("Search and Filtering Demo")
    
    service = ItemService()
    
    # Create diverse test data
    test_items = [
        ItemCreate(name="iPhone 15 Pro", price=999.99, is_offer=False),
        ItemCreate(name="Samsung Galaxy S24", price=799.99, is_offer=True),
        ItemCreate(name="Google Pixel 8", price=699.99, is_offer=False),
        ItemCreate(name="iPhone 15", price=799.99, is_offer=True),
        ItemCreate(name="MacBook Air", price=1199.99, is_offer=False),
        ItemCreate(name="Surface Laptop", price=1099.99, is_offer=True),
        ItemCreate(name="ThinkPad X1", price=1299.99, is_offer=False),
        ItemCreate(name="AirPods Pro", price=249.99, is_offer=True),
        ItemCreate(name="Sony Headphones", price=349.99, is_offer=False),
    ]
    
    for item_data in test_items:
        await service.create_item(item_data)
    
    print("✓ Search operations:")
    
    # Search tests
    search_queries = ["iPhone", "laptop", "headphones", "galaxy"]
    
    for query in search_queries:
        pagination = PaginationParams(page=1, limit=5)
        results = await service.search_items(query, pagination)
        
        print(f"\n  Search '{query}': {results.total} results")
        for item in results.items:
            print(f"    - {item.name}: ${item.price}")
    
    print(f"\n✓ Filtering operations:")
    
    # Filter tests
    filter_tests = [
        {"min_price": 800, "description": "Items $800+"},
        {"max_price": 300, "description": "Items under $300"},
        {"is_offer": True, "description": "Items on offer"},
        {"min_price": 1000, "max_price": 1500, "description": "Items $1000-$1500"},
        {"name_contains": "pro", "description": "Items with 'pro' in name"},
    ]
    
    for filter_test in filter_tests:
        description = filter_test.pop("description")
        pagination = PaginationParams(page=1, limit=10)
        results = await service.filter_items(filter_test, pagination)
        
        print(f"\n  {description}: {results.total} results")
        for item in results.items:
            offer_flag = " (OFFER)" if item.is_offer else ""
            print(f"    - {item.name}: ${item.price}{offer_flag}")


async def demo_pagination():
    """Demonstrate pagination functionality."""
    print_banner("Pagination Demo")
    
    service = ItemService()
    
    # Create a larger dataset for pagination testing
    print("✓ Creating test dataset...")
    
    item_names = [
        "Laptop", "Mouse", "Keyboard", "Monitor", "Speaker", "Headphones",
        "Tablet", "Phone", "Charger", "Cable", "Drive", "Camera",
        "Printer", "Scanner", "Router", "Switch", "Hub", "Dock",
        "Stand", "Case", "Cover", "Protector", "Adapter", "Converter"
    ]
    
    for i, base_name in enumerate(item_names):
        for variant in range(1, 4):  # Create 3 variants of each
            name = f"{base_name} Model {variant}"
            price = round(random.uniform(29.99, 999.99), 2)
            is_offer = random.choice([True, False])
            
            await service.create_item(ItemCreate(name=name, price=price, is_offer=is_offer))
    
    print(f"  Created {len(item_names) * 3} items")
    
    print(f"\n✓ Pagination scenarios:")
    
    # Test different pagination scenarios
    pagination_tests = [
        {"page": 1, "limit": 10, "description": "First page (10 items)"},
        {"page": 2, "limit": 10, "description": "Second page (10 items)"},
        {"page": 1, "limit": 5, "description": "First page (5 items)"},
        {"page": 3, "limit": 15, "description": "Third page (15 items)"},
        {"page": 1, "limit": 100, "description": "Large page (100 items)"},
    ]
    
    for test in pagination_tests:
        pagination = PaginationParams(page=test["page"], limit=test["limit"])
        results = await service.get_items(pagination)
        
        print(f"\n  {test['description']}:")
        print(f"    Total items: {results.total}")
        print(f"    Page {results.page} of {results.pages}")
        print(f"    Showing {len(results.items)} items")
        
        # Show first few items from this page
        for i, item in enumerate(results.items[:3]):
            print(f"      {pagination.offset + i + 1}. {item.name}")
        
        if len(results.items) > 3:
            print(f"      ... and {len(results.items) - 3} more")
    
    # Test edge cases
    print(f"\n✓ Edge case testing:")
    
    # Page beyond available data
    pagination = PaginationParams(page=100, limit=10)
    results = await service.get_items(pagination)
    print(f"  Page 100: {len(results.items)} items (expected: 0)")
    
    # Large limit
    pagination = PaginationParams(page=1, limit=1000)
    results = await service.get_items(pagination)
    print(f"  Limit 1000: Got {len(results.items)} items (max available)")


async def demo_validation_and_errors():
    """Demonstrate validation and error handling."""
    print_banner("Validation and Error Handling Demo")
    
    service = ItemService()
    
    print("✓ Input validation tests:")
    
    # Test various validation scenarios
    validation_tests = [
        {"data": ItemCreate(name="", price=10.99), "description": "Empty name"},
        {"data": ItemCreate(name="Valid Product", price=-5.99), "description": "Negative price"},
        {"data": ItemCreate(name="x" * 101, price=10.99), "description": "Name too long"},
        {"data": ItemCreate(name="Valid Product", price=1000000.00), "description": "Price too high"},
        {"data": ItemCreate(name="spam product", price=10.99), "description": "Prohibited content"},
        {"data": ItemCreate(name="Valid Product", price=29.99), "description": "Valid item"},
    ]
    
    for test in validation_tests:
        try:
            item = await service.create_item(test["data"])
            print(f"  ✓ {test['description']}: Created successfully (ID: {item.id})")
        except ValidationError as e:
            print(f"  ✗ {test['description']}: {e}")
    
    print(f"\n✓ Update validation tests:")
    
    # Create a valid item first
    valid_item = await service.create_item(ItemCreate(name="Sample Product", price=50.00))
    
    update_tests = [
        {"data": ItemUpdate(name=""), "description": "Empty name update"},
        {"data": ItemUpdate(price=-10.00), "description": "Negative price update"},
        {"data": ItemUpdate(name="Updated Product"), "description": "Valid name update"},
        {"data": ItemUpdate(price=75.00), "description": "Valid price update"},
    ]
    
    for test in update_tests:
        try:
            updated = await service.update_item(valid_item.id, test["data"])
            if updated:
                print(f"  ✓ {test['description']}: Updated successfully")
            else:
                print(f"  ✗ {test['description']}: Item not found")
        except ValidationError as e:
            print(f"  ✗ {test['description']}: {e}")
    
    print(f"\n✓ Error handling scenarios:")
    
    # Test error scenarios
    print(f"  Update non-existent item:")
    try:
        result = await service.update_item(999, ItemUpdate(name="New Name"))
        print(f"    Result: {'Success' if result else 'Item not found (expected)'}")
    except ValidationError as e:
        print(f"    Error: {e}")
    
    print(f"  Delete non-existent item:")
    success = await service.delete_item(999)
    print(f"    Result: {'Success' if success else 'Item not found (expected)'}")


async def demo_business_logic():
    """Demonstrate business logic and statistics."""
    print_banner("Business Logic Demo")
    
    service = ItemService()
    
    # Create diverse product data
    print("✓ Creating business dataset...")
    
    business_items = [
        ItemCreate(name="Premium Laptop", price=1899.99, is_offer=False),
        ItemCreate(name="Basic Laptop", price=599.99, is_offer=True),
        ItemCreate(name="Gaming Mouse", price=79.99, is_offer=False),
        ItemCreate(name="Office Mouse", price=19.99, is_offer=True),
        ItemCreate(name="Mechanical Keyboard", price=149.99, is_offer=False),
        ItemCreate(name="Wireless Keyboard", price=49.99, is_offer=True),
        ItemCreate(name="4K Monitor", price=499.99, is_offer=False),
        ItemCreate(name="HD Monitor", price=199.99, is_offer=True),
        ItemCreate(name="Webcam", price=89.99, is_offer=False),
        ItemCreate(name="Headset", price=129.99, is_offer=True),
    ]
    
    for item_data in business_items:
        await service.create_item(item_data)
    
    print(f"  Created {len(business_items)} products")
    
    print(f"\n✓ Business statistics:")
    
    stats = await service.get_statistics()
    
    print(f"  Total Items: {stats['total_items']}")
    print(f"  Average Price: ${stats['average_price']}")
    print(f"  Price Range: ${stats['min_price']} - ${stats['max_price']}")
    print(f"  Items on Offer: {stats['offers_count']} ({stats['offers_percentage']}%)")
    
    print(f"\n✓ Business rules demonstration:")
    
    # Demonstrate business logic
    print(f"  Price categorization:")
    
    pagination = PaginationParams(page=1, limit=50)
    all_items = await service.get_items(pagination)
    
    budget_items = [item for item in all_items.items if item.price < 50]
    mid_range_items = [item for item in all_items.items if 50 <= item.price < 200]
    premium_items = [item for item in all_items.items if item.price >= 200]
    
    print(f"    Budget (<$50): {len(budget_items)} items")
    print(f"    Mid-range ($50-$200): {len(mid_range_items)} items")
    print(f"    Premium ($200+): {len(premium_items)} items")
    
    print(f"\n  Offer analysis:")
    offer_items = [item for item in all_items.items if item.is_offer]
    regular_items = [item for item in all_items.items if not item.is_offer]
    
    if offer_items:
        avg_offer_price = sum(item.price for item in offer_items) / len(offer_items)
        print(f"    Average offer price: ${avg_offer_price:.2f}")
    
    if regular_items:
        avg_regular_price = sum(item.price for item in regular_items) / len(regular_items)
        print(f"    Average regular price: ${avg_regular_price:.2f}")
    
    print(f"\n  Inventory recommendations:")
    
    if stats['offers_percentage'] < 20:
        print(f"    ⚠️  Low offer percentage - consider more promotions")
    elif stats['offers_percentage'] > 50:
        print(f"    ⚠️  High offer percentage - may impact profitability")
    else:
        print(f"    ✓ Healthy offer balance")
    
    if len(premium_items) < 3:
        print(f"    💡 Consider adding more premium products")
    
    if len(budget_items) < 3:
        print(f"    💡 Consider adding more budget-friendly options")


async def main():
    """Run the complete Items API demo."""
    print_banner("Items API Demo")
    print("This demo showcases the Items API with CRUD, search, and business logic.")
    
    try:
        # CRUD operations
        await demo_crud_operations()
        
        # Search and filtering
        await demo_search_and_filtering()
        
        # Pagination
        await demo_pagination()
        
        # Validation and error handling
        await demo_validation_and_errors()
        
        # Business logic
        await demo_business_logic()
        
        print_banner("Items API Demo Complete")
        print("✓ All Items API features demonstrated successfully!")
        print("\nKey Features Covered:")
        print("- CRUD operations (Create, Read, Update, Delete)")
        print("- Search functionality with text matching")
        print("- Advanced filtering with multiple criteria")
        print("- Pagination with configurable page sizes")
        print("- Input validation and business rule enforcement")
        print("- Error handling and user-friendly messages")
        print("- Business logic and statistical analysis")
        print("- API response models and data structures")
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        raise


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())