"""Tests for WebAuthn service functionality."""
import base64
import json
import secrets
from unittest.mock import patch

import pytest
from app.auth.webauthn_service import WebAuthnService


class TestWebAuthnService:
    """Test WebAuthn service core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = WebAuthnService(rp_id="localhost", rp_name="Test App")
    
    def test_generate_challenge(self):
        """Test challenge generation."""
        challenge = self.service.generate_challenge()
        
        # Challenge should be base64url encoded
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        
        # Should be decodable
        decoded = base64.urlsafe_b64decode(challenge + '==')
        assert len(decoded) == 32
    
    def test_store_and_get_challenge(self):
        """Test challenge storage and retrieval."""
        user_id = 1
        challenge = "test_challenge"
        
        # Store challenge
        self.service.store_challenge(user_id, challenge)
        
        # Retrieve challenge
        retrieved = self.service.get_challenge(user_id)
        assert retrieved == challenge
    
    def test_get_expired_challenge(self):
        """Test that expired challenges return None."""
        user_id = 1
        challenge = "test_challenge"
        
        # Store with very short expiry
        self.service.store_challenge(user_id, challenge, expires_in=-1)
        
        # Should return None for expired challenge
        retrieved = self.service.get_challenge(user_id)
        assert retrieved is None
    
    def test_clear_challenge(self):
        """Test challenge clearing."""
        user_id = 1
        challenge = "test_challenge"
        
        # Store and clear
        self.service.store_challenge(user_id, challenge)
        self.service.clear_challenge(user_id)
        
        # Should return None after clearing
        retrieved = self.service.get_challenge(user_id)
        assert retrieved is None
    
    def test_create_registration_options(self):
        """Test WebAuthn registration options creation."""
        user_id = 1
        username = "testuser"
        display_name = "Test User"
        
        options = self.service.create_registration_options(user_id, username, display_name)
        
        # Check required fields
        assert "challenge" in options
        assert "rp" in options
        assert "user" in options
        assert "pubKeyCredParams" in options
        assert "timeout" in options
        assert "attestation" in options
        assert "authenticatorSelection" in options
        
        # Check values
        assert options["rp"]["id"] == "localhost"
        assert options["rp"]["name"] == "Test App"
        assert options["user"]["name"] == username
        assert options["user"]["displayName"] == display_name
        assert options["timeout"] == 60000
        assert options["attestation"] == "none"
        
        # Check that challenge is stored
        stored_challenge = self.service.get_challenge(user_id)
        assert stored_challenge == options["challenge"]
    
    def test_create_authentication_options(self):
        """Test WebAuthn authentication options creation."""
        user_id = 1
        
        options, challenge = self.service.create_authentication_options(user_id)
        
        # Check required fields
        assert "challenge" in options
        assert "timeout" in options
        assert "rpId" in options
        assert "allowCredentials" in options
        assert "userVerification" in options
        
        # Check values
        assert options["rpId"] == "localhost"
        assert options["timeout"] == 60000
        assert options["userVerification"] == "required"
        assert isinstance(options["allowCredentials"], list)
        
        # Check that challenge is stored
        stored_challenge = self.service.get_challenge(user_id)
        assert stored_challenge == challenge
    
    def test_create_authentication_options_usernameless(self):
        """Test usernameless authentication options."""
        options, challenge = self.service.create_authentication_options()
        
        # Should still create valid options without user_id
        assert "challenge" in options
        assert options["rpId"] == "localhost"
        assert isinstance(challenge, str)
        assert len(challenge) > 0
    
    def test_decode_base64url(self):
        """Test base64url decoding utility."""
        # Test with padding needed
        data = "SGVsbG8gV29ybGQ"  # "Hello World" without padding
        decoded = self.service._decode_base64url(data)
        assert decoded == b"Hello World"
        
        # Test with no padding needed  
        data_with_padding = "SGVsbG8gV29ybGQh"  # "Hello World!" 
        decoded = self.service._decode_base64url(data_with_padding)
        assert decoded == b"Hello World!"
    
    def test_verify_registration_response_no_challenge(self):
        """Test registration verification fails without challenge."""
        user_id = 1
        mock_response = {
            "response": {
                "attestationObject": "mock_attestation",
                "clientDataJSON": "mock_client_data"
            }
        }
        
        success, result = self.service.verify_registration_response(user_id, mock_response)
        assert not success
        assert "No challenge found" in result["error"]
    
    def test_verify_authentication_response_challenge_mismatch(self):
        """Test authentication verification fails with wrong challenge."""
        mock_response = {
            "response": {
                "authenticatorData": base64.urlsafe_b64encode(b"mock_auth_data").decode(),
                "clientDataJSON": base64.urlsafe_b64encode(
                    json.dumps({"challenge": "wrong_challenge", "origin": "http://localhost:8000"}).encode()
                ).decode(),
                "signature": base64.urlsafe_b64encode(b"mock_signature").decode()
            }
        }
        
        success, result = self.service.verify_authentication_response(
            "credential_id", b"public_key", 0, mock_response, "correct_challenge"
        )
        
        assert not success
        assert "Challenge mismatch" in result["error"]


class TestWebAuthnServiceGlobal:
    """Test the global WebAuthn service instance."""
    
    def test_global_instance_creation(self):
        """Test that global service instance is created properly."""
        from app.auth.webauthn_service import webauthn_service
        
        assert webauthn_service is not None
        assert isinstance(webauthn_service, WebAuthnService)
        assert webauthn_service.rp_id == "localhost"  # From default config