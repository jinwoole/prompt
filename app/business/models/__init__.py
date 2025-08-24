"""Business domain models and DTOs.

Place your business domain models here. These should represent
your core business concepts and be independent of database 
or API concerns.

Example:
    class Product:
        def __init__(self, name: str, price: Decimal):
            self.name = name
            self.price = price
            
        def apply_discount(self, percentage: Decimal) -> Decimal:
            return self.price * (1 - percentage / 100)
"""