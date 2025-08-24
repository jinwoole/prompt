"""Business-specific exceptions.

Define custom exceptions for your business logic here. These should
represent business rule violations and domain-specific errors.

Example:
    class InsufficientInventoryError(Exception):
        def __init__(self, product_id: int, requested: int, available: int):
            self.product_id = product_id
            self.requested = requested
            self.available = available
            super().__init__(f"Insufficient inventory for product {product_id}: requested {requested}, available {available}")
            
    class InvalidDiscountError(Exception):
        def __init__(self, discount_percentage: float):
            self.discount_percentage = discount_percentage
            super().__init__(f"Invalid discount percentage: {discount_percentage}%")
"""