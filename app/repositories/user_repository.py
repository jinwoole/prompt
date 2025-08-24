"""User repository for database operations."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entities import User
from app.auth.models import UserCreate, UserUpdate
from app.auth.security import get_password_hash


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(user_data.password)
        
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
        )
        
        self.db.add(db_user)
        
        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("User with this email or username already exists")
    
    async def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        # Handle password hashing if password is being updated
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("User with this email or username already exists")
    
    async def delete(self, user_id: int) -> bool:
        """Delete a user."""
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return False
        
        await self.db.delete(db_user)
        await self.db.commit()
        return True
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username/email and password."""
        from app.auth.security import verify_password
        
        # Try to find user by username or email
        user = await self.get_by_username(username)
        if not user:
            user = await self.get_by_email(username)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user