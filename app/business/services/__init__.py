"""Business services and core logic.

Implement your business rules and workflows here. Services should
contain the core business logic and orchestrate between repositories
and external services.

Example:
    class OrderService:
        def __init__(self, order_repo: OrderRepository, payment_service: PaymentService):
            self.order_repo = order_repo
            self.payment_service = payment_service
            
        async def create_order(self, order_data: CreateOrderDTO) -> Order:
            # Business logic here
            order = Order.from_dto(order_data)
            order.calculate_total()
            
            if order.total > 0:
                await self.payment_service.process_payment(order.payment_info)
            
            return await self.order_repo.save(order)
"""