"""Business interfaces for external dependencies.

Define abstract interfaces here for external services, repositories,
and other dependencies. This allows for better testing and
dependency inversion.

Example:
    from abc import ABC, abstractmethod
    
    class PaymentGateway(ABC):
        @abstractmethod
        async def process_payment(self, payment_info: PaymentInfo) -> PaymentResult:
            pass
            
    class EmailService(ABC):
        @abstractmethod  
        async def send_email(self, to: str, subject: str, body: str) -> bool:
            pass
"""