"""Tests for passkey authentication functionality."""
import base64
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import get_db_session
from app.repositories.user_repository import UserRepository
from app.repositories.passkey_repository import PasskeyCredentialRepository
from app.auth.models import UserCreate
from app.auth.webauthn_service import webauthn_service
from app.auth.passkey_models import PasskeyCredentialCreate


# Use mock database for passkey tests to avoid DB connection issues
import os
os.environ["USE_MOCK_DB"] = "true"

client = TestClient(app)


@pytest_asyncio.fixture
async def async_test_user(db_session: AsyncSession):
    """Create a test user using async session."""
    user_repo = UserRepository(db_session)
    user_data = UserCreate(
        email="testuser@example.com",
        username="testuser",
        password="testpassword123"
    )
    user = await user_repo.create(user_data)
    await db_session.commit()
    return user


@pytest.fixture
def mock_webauthn_service():
    """Mock WebAuthn service for testing."""
    with patch('app.api.passkey.webauthn_service') as mock:
        yield mock


class TestPasskeyRegistration:
    """Test passkey registration endpoints."""
    
    @pytest.mark.asyncio
    async def test_begin_passkey_registration_success(self, async_test_user, db_session):
        """Test beginning passkey registration for valid user."""
        
        # Mock database session  
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        request_data = {
            "username": async_test_user.username
        }
        
        try:
            response = client.post("/api/v1/passkey/register/begin", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required WebAuthn fields
            assert "challenge" in data
            assert "rp" in data
            assert "user" in data
            assert "pubKeyCredParams" in data
            assert data["rp"]["id"] == "localhost"
            assert data["user"]["name"] == async_test_user.username
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_begin_passkey_registration_user_not_found(self, db_session):
        """Test beginning passkey registration for non-existent user."""
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        request_data = {
            "username": "nonexistent"
        }
        
        try:
            response = client.post("/api/v1/passkey/register/begin", json=request_data)
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestPasskeyAuthentication:
    """Test passkey authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_begin_passkey_authentication_usernameless(self, db_session):
        """Test beginning usernameless passkey authentication."""
        
        def get_test_db():
            return db_session
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        # For usernameless authentication, send empty JSON body
        request_data = {}
        
        try:
            response = client.post("/api/v1/passkey/authenticate/begin", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required WebAuthn fields
            assert "challenge" in data
            assert "allowCredentials" in data
            assert "rpId" in data
            assert data["rpId"] == "localhost"
        finally:
            app.dependency_overrides.clear()


class TestWebAuthnService:
    """Test WebAuthn service functionality."""
    
    def test_generate_challenge(self):
        """Test challenge generation."""
        challenge = webauthn_service.generate_challenge()
        
        # Challenge should be base64 encoded string
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        
        # Should be able to decode
        import base64
        decoded = base64.urlsafe_b64decode(challenge + '==')
        assert len(decoded) >= 16  # At least 16 bytes
    
    def test_challenge_storage_and_retrieval(self):
        """Test storing and retrieving challenges."""
        challenge = "test_challenge_123"
        user_id = 123  # Use numeric user ID
        
        # Store challenge
        webauthn_service.store_challenge(user_id, challenge)
        
        # Retrieve challenge
        stored_challenge = webauthn_service.get_challenge(user_id)
        assert stored_challenge == challenge
        
        # Challenge should still be available (not consumed automatically)
        available_challenge = webauthn_service.get_challenge(user_id)
        assert available_challenge == challenge
        
        # Clear challenge manually
        webauthn_service.clear_challenge(user_id)
        cleared_challenge = webauthn_service.get_challenge(user_id)
        assert cleared_challenge is None
    
    def test_challenge_expiration(self):
        """Test challenge expiration."""
        import time
        
        challenge = "test_challenge_expired"
        user_id = 124  # Use numeric user ID
        
        # Store challenge with short expiration
        webauthn_service.store_challenge(user_id, challenge, expires_in=1)
        
        # Should be available immediately
        stored_challenge = webauthn_service.get_challenge(user_id)
        assert stored_challenge == challenge
        
        # Store again and wait for expiration
        webauthn_service.store_challenge(user_id, challenge, expires_in=1)
        time.sleep(2)
        
        # Should be expired
        expired_challenge = webauthn_service.get_challenge(user_id)
        assert expired_challenge is None
    
    def test_create_registration_options(self):
        """Test creating registration options."""
        user_id = 123
        username = 'testuser'
        display_name = 'Test User'
        
        options = webauthn_service.create_registration_options(user_id, username, display_name)
        
        assert "challenge" in options
        assert "rp" in options
        assert "user" in options
        assert "pubKeyCredParams" in options
        assert options["rp"]["id"] == "localhost"
        assert options["user"]["name"] == username
        assert options["user"]["displayName"] == display_name
    
    def test_create_authentication_options(self):
        """Test creating authentication options."""
        credentials = []  # Empty for usernameless authentication
        
        result = webauthn_service.create_authentication_options(allow_credentials=credentials)
        options, challenge = result
        
        assert "challenge" in options
        assert "allowCredentials" in options
        assert "rpId" in options
        assert options["rpId"] == "localhost"
        assert isinstance(options["allowCredentials"], list)
        assert isinstance(challenge, str)