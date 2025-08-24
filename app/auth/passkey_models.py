"""Passkey authentication models and schemas."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class PasskeyCredentialBase(BaseModel):
    """Base passkey credential model."""
    name: Optional[str] = Field(None, description="User-friendly name for the credential")


class PasskeyCredentialCreate(PasskeyCredentialBase):
    """Passkey credential creation model."""
    credential_id: str = Field(..., description="Base64URL encoded credential ID")
    public_key: bytes = Field(..., description="CBOR encoded public key")
    sign_count: int = Field(0, description="Initial signature counter")


class PasskeyCredential(PasskeyCredentialBase):
    """Passkey credential model for API responses."""
    id: int
    credential_id: str
    sign_count: int
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class WebAuthnRegistrationChallenge(BaseModel):
    """WebAuthn registration challenge response."""
    challenge: str = Field(..., description="Base64URL encoded challenge")
    rp: Dict[str, str] = Field(..., description="Relying Party information")
    user: Dict[str, Any] = Field(..., description="User information")
    pubKeyCredParams: list = Field(..., description="Supported public key algorithms")
    timeout: int = Field(60000, description="Timeout in milliseconds")
    attestation: str = Field("none", description="Attestation preference")
    authenticatorSelection: Dict[str, Any] = Field(..., description="Authenticator selection criteria")
    excludeCredentials: list = Field(default_factory=list, description="Excluded credentials")


class WebAuthnAuthenticationChallenge(BaseModel):
    """WebAuthn authentication challenge response."""
    challenge: str = Field(..., description="Base64URL encoded challenge")
    timeout: int = Field(60000, description="Timeout in milliseconds")
    rpId: str = Field(..., description="Relying Party ID")
    allowCredentials: list = Field(..., description="Allowed credentials")
    userVerification: str = Field("required", description="User verification requirement")


class WebAuthnRegistrationResponse(BaseModel):
    """WebAuthn registration response from client."""
    id: str = Field(..., description="Credential ID")
    rawId: str = Field(..., description="Raw credential ID (base64url)")
    response: Dict[str, str] = Field(..., description="Authenticator response")
    type: str = Field("public-key", description="Credential type")
    clientExtensionResults: Dict[str, Any] = Field(default_factory=dict, description="Client extension results")
    name: Optional[str] = Field(None, description="User-friendly name for the credential")


class WebAuthnAuthenticationResponse(BaseModel):
    """WebAuthn authentication response from client."""
    id: str = Field(..., description="Credential ID")
    rawId: str = Field(..., description="Raw credential ID (base64url)")
    response: Dict[str, str] = Field(..., description="Authenticator response")
    type: str = Field("public-key", description="Credential type")
    clientExtensionResults: Dict[str, Any] = Field(default_factory=dict, description="Client extension results")


class PasskeyRegistrationRequest(BaseModel):
    """Request to initiate passkey registration."""
    username: str = Field(..., description="Username for the account")


class PasskeyAuthenticationRequest(BaseModel):
    """Request to initiate passkey authentication."""
    username: Optional[str] = Field(None, description="Username (optional for usernameless flow)")


class PasskeyTokenResponse(BaseModel):
    """Token response after successful passkey authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]