"""
Database entity models using SQLAlchemy.
Defines the database schema and ORM mappings.
"""
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User database model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to passkey credentials
    passkey_credentials = relationship("PasskeyCredential", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class PasskeyCredential(Base):
    """Passkey credential database model for WebAuthn."""
    __tablename__ = "passkey_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    credential_id = Column(String(255), unique=True, index=True, nullable=False)  # Base64URL encoded
    public_key = Column(LargeBinary, nullable=False)  # CBOR encoded public key
    sign_count = Column(Integer, default=0, nullable=False)
    name = Column(String(255), nullable=True)  # User-friendly name for the credential
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationship to user
    user = relationship("User", back_populates="passkey_credentials")
    
    def __repr__(self):
        return f"<PasskeyCredential(id={self.id}, user_id={self.user_id}, credential_id='{self.credential_id[:10]}...')>"


class Item(Base):
    """Item database model."""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False, index=True)
    is_offer = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', price={self.price})>"


class MockItem:
    """Mock Item model for when using mock database."""
    
    def __init__(self, id: int, name: str, price: float, is_offer: Optional[bool] = None):
        self.id = id
        self.name = name
        self.price = price
        self.is_offer = is_offer if is_offer is not None else False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def __repr__(self):
        return f"<MockItem(id={self.id}, name='{self.name}', price={self.price})>"


# Mock in-memory storage for demonstration when USE_MOCK_DB=true
_items_storage = {}
_next_id = 1


def get_next_id() -> int:
    """Get next available ID for mock storage."""
    global _next_id
    current_id = _next_id
    _next_id += 1
    return current_id


def reset_storage():
    """Reset mock storage (useful for testing)."""
    global _items_storage, _next_id
    _items_storage = {}
    _next_id = 1