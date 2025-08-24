"""Repository for passkey credential operations."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.entities import PasskeyCredential, User
from app.auth.passkey_models import PasskeyCredentialCreate


class PasskeyCredentialRepository:
    """Repository for passkey credential database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, user_id: int, credential_data: PasskeyCredentialCreate) -> PasskeyCredential:
        """Create a new passkey credential."""
        db_credential = PasskeyCredential(
            user_id=user_id,
            credential_id=credential_data.credential_id,
            public_key=credential_data.public_key,
            sign_count=credential_data.sign_count,
            name=credential_data.name,
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        self.db.add(db_credential)
        await self.db.commit()
        await self.db.refresh(db_credential)
        return db_credential
    
    async def get_by_credential_id(self, credential_id: str) -> Optional[PasskeyCredential]:
        """Get passkey credential by credential ID."""
        result = await self.db.execute(
            select(PasskeyCredential)
            .options(selectinload(PasskeyCredential.user))
            .where(PasskeyCredential.credential_id == credential_id)
            .where(PasskeyCredential.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: int) -> List[PasskeyCredential]:
        """Get all active passkey credentials for a user."""
        result = await self.db.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.user_id == user_id)
            .where(PasskeyCredential.is_active == True)
            .order_by(PasskeyCredential.created_at.desc())
        )
        return result.scalars().all()
    
    async def update_sign_count(self, credential_id: str, sign_count: int) -> bool:
        """Update the sign count for a credential."""
        result = await self.db.execute(
            update(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .where(PasskeyCredential.is_active == True)
            .values(sign_count=sign_count, last_used=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def deactivate(self, credential_id: str, user_id: int) -> bool:
        """Deactivate a passkey credential."""
        result = await self.db.execute(
            update(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .where(PasskeyCredential.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def delete(self, credential_id: str, user_id: int) -> bool:
        """Delete a passkey credential permanently."""
        result = await self.db.execute(
            delete(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .where(PasskeyCredential.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def get_credential_ids_for_user(self, user_id: int) -> List[str]:
        """Get all credential IDs for a user (for exclusion in registration)."""
        result = await self.db.execute(
            select(PasskeyCredential.credential_id)
            .where(PasskeyCredential.user_id == user_id)
            .where(PasskeyCredential.is_active == True)
        )
        return [row[0] for row in result.fetchall()]