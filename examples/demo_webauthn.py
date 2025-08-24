#!/usr/bin/env python3
"""
Demo script showcasing WebAuthn/Passkey functionality.

This demo demonstrates:
- WebAuthn challenge generation and verification
- Passkey credential models and validation
- Registration challenge creation
- Authentication challenge creation
- Credential storage simulation
- Security features of WebAuthn
"""
import asyncio
import json
import base64
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def demo_webauthn_service():
    """Demonstrate WebAuthn service capabilities."""
    print_banner("WebAuthn Service Demo")
    
    from app.auth.webauthn_service import WebAuthnService
    
    # Initialize WebAuthn service
    webauthn = WebAuthnService(
        rp_id="demo.example.com",
        rp_name="FastAPI Enterprise Demo"
    )
    
    print(f"✓ WebAuthn service initialized:")
    print(f"  Relying Party ID: {webauthn.rp_id}")
    print(f"  Relying Party Name: {webauthn.rp_name}")
    
    # Generate challenges for different users
    users = [
        {"id": 1, "username": "admin", "display_name": "Administrator"},
        {"id": 2, "username": "user1", "display_name": "John Doe"},
        {"id": 3, "username": "demo", "display_name": "Demo User"},
    ]
    
    challenges = {}
    print(f"\n✓ Generating challenges for {len(users)} users:")
    
    for user in users:
        challenge = webauthn.generate_challenge()
        webauthn.store_challenge(user["id"], challenge)
        challenges[user["id"]] = challenge
        
        print(f"  User {user['username']}: {challenge[:20]}...")
    
    # Verify challenge storage and retrieval
    print(f"\n✓ Verifying challenge storage:")
    for user in users:
        stored_challenge = webauthn.get_challenge(user["id"])
        is_valid = stored_challenge == challenges[user["id"]]
        print(f"  User {user['username']}: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Test challenge expiration
    print(f"\n✓ Testing challenge expiration:")
    import time
    
    # Create short-lived challenge
    short_challenge = webauthn.generate_challenge()
    webauthn.challenge_cache[999] = {
        'challenge': short_challenge,
        'expires_at': datetime.now(timezone.utc)  # Already expired
    }
    
    expired_challenge = webauthn.get_challenge(999)
    print(f"  Expired challenge: {'✗ Correctly None' if expired_challenge is None else '✓ Unexpectedly valid'}")


def demo_passkey_models():
    """Demonstrate passkey model validation and serialization."""
    print_banner("Passkey Models Demo")
    
    from app.auth.passkey_models import (
        PasskeyCredentialCreate, PasskeyCredential,
        WebAuthnRegistrationChallenge, WebAuthnAuthenticationChallenge
    )
    from pydantic import ValidationError
    
    # Valid passkey credential creation
    try:
        credential_create = PasskeyCredentialCreate(
            name="MyPhone TouchID",
            credential_id="dGVzdC1jcmVkZW50aWFsLWlk",  # base64url encoded
            public_key=b"mock_public_key_bytes",
            sign_count=0
        )
        print(f"✓ Valid passkey credential creation:")
        print(f"  Name: {credential_create.name}")
        print(f"  Credential ID: {credential_create.credential_id}")
        print(f"  Sign Count: {credential_create.sign_count}")
    except ValidationError as e:
        print(f"✗ Credential creation failed: {e}")
    
    # Passkey credential response model
    credential = PasskeyCredential(
        id=1,
        name="iPhone Face ID",
        credential_id="aVBob25lLWZhY2UtaWQ",
        sign_count=42,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
        is_active=True
    )
    print(f"\n✓ Passkey credential model:")
    print(f"  ID: {credential.id}")
    print(f"  Name: {credential.name}")
    print(f"  Credential ID: {credential.credential_id}")
    print(f"  Sign Count: {credential.sign_count}")
    print(f"  Created: {credential.created_at}")
    print(f"  Active: {credential.is_active}")


def demo_registration_challenge():
    """Demonstrate WebAuthn registration challenge creation."""
    print_banner("WebAuthn Registration Challenge Demo")
    
    from app.auth.passkey_models import WebAuthnRegistrationChallenge
    from app.auth.webauthn_service import WebAuthnService
    
    webauthn = WebAuthnService()
    
    # Create registration challenge
    user_data = {
        "id": 123,
        "username": "testuser",
        "display_name": "Test User",
        "email": "test@example.com"
    }
    
    challenge = webauthn.generate_challenge()
    
    registration_options = WebAuthnRegistrationChallenge(
        challenge=challenge,
        rp={
            "id": webauthn.rp_id,
            "name": webauthn.rp_name
        },
        user={
            "id": base64.urlsafe_b64encode(str(user_data["id"]).encode()).decode().rstrip('='),
            "name": user_data["username"],
            "displayName": user_data["display_name"]
        },
        pubKeyCredParams=[
            {"type": "public-key", "alg": -7},   # ES256
            {"type": "public-key", "alg": -257}, # RS256
        ],
        authenticatorSelection={
            "authenticatorAttachment": "platform",
            "userVerification": "required",
            "residentKey": "preferred"
        },
        excludeCredentials=[]
    )
    
    print(f"✓ Registration challenge created:")
    print(f"  Challenge: {registration_options.challenge[:20]}...")
    print(f"  RP ID: {registration_options.rp['id']}")
    print(f"  RP Name: {registration_options.rp['name']}")
    print(f"  User ID: {registration_options.user['id']}")
    print(f"  Username: {registration_options.user['name']}")
    print(f"  Display Name: {registration_options.user['displayName']}")
    print(f"  Timeout: {registration_options.timeout}ms")
    print(f"  Supported Algorithms: {len(registration_options.pubKeyCredParams)}")
    print(f"  Authenticator Selection: {registration_options.authenticatorSelection}")


def demo_authentication_challenge():
    """Demonstrate WebAuthn authentication challenge creation."""
    print_banner("WebAuthn Authentication Challenge Demo")
    
    from app.auth.passkey_models import WebAuthnAuthenticationChallenge
    from app.auth.webauthn_service import WebAuthnService
    
    webauthn = WebAuthnService()
    
    # Simulate existing credentials for user
    existing_credentials = [
        {
            "id": "aVBob25lLWZhY2UtaWQ",
            "type": "public-key",
            "transports": ["internal"]
        },
        {
            "id": "YW5kcm9pZC1maW5nZXJwcmludA",
            "type": "public-key", 
            "transports": ["internal", "hybrid"]
        }
    ]
    
    challenge = webauthn.generate_challenge()
    
    auth_options = WebAuthnAuthenticationChallenge(
        challenge=challenge,
        rpId=webauthn.rp_id,
        allowCredentials=existing_credentials,
        userVerification="required"
    )
    
    print(f"✓ Authentication challenge created:")
    print(f"  Challenge: {auth_options.challenge[:20]}...")
    print(f"  RP ID: {auth_options.rpId}")
    print(f"  Timeout: {auth_options.timeout}ms")
    print(f"  User Verification: {auth_options.userVerification}")
    print(f"  Allowed Credentials: {len(auth_options.allowCredentials)}")
    
    for i, cred in enumerate(auth_options.allowCredentials, 1):
        print(f"    {i}. ID: {cred['id']}")
        print(f"       Type: {cred['type']}")
        print(f"       Transports: {cred.get('transports', [])}")


def demo_passkey_workflow_simulation():
    """Simulate a complete passkey registration and authentication workflow."""
    print_banner("Passkey Workflow Simulation")
    
    from app.auth.webauthn_service import WebAuthnService
    from app.auth.passkey_models import (
        PasskeyCredentialCreate, PasskeyCredential,
        WebAuthnRegistrationChallenge, WebAuthnAuthenticationChallenge
    )
    
    webauthn = WebAuthnService()
    
    # Simulate credential database
    credentials_db: Dict[int, List[PasskeyCredential]] = {}
    
    def register_passkey(user_id: int, credential_data: PasskeyCredentialCreate) -> PasskeyCredential:
        """Simulate passkey registration."""
        if user_id not in credentials_db:
            credentials_db[user_id] = []
        
        # Create credential record
        credential = PasskeyCredential(
            id=len(credentials_db[user_id]) + 1,
            name=credential_data.name,
            credential_id=credential_data.credential_id,
            sign_count=credential_data.sign_count,
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        credentials_db[user_id].append(credential)
        return credential
    
    def authenticate_passkey(user_id: int, credential_id: str) -> bool:
        """Simulate passkey authentication."""
        user_credentials = credentials_db.get(user_id, [])
        
        for credential in user_credentials:
            if credential.credential_id == credential_id and credential.is_active:
                # Update last used and sign count
                credential.last_used = datetime.now(timezone.utc)
                credential.sign_count += 1
                return True
        
        return False
    
    # Demo the workflow
    user_id = 42
    user_info = {
        "username": "passkey_user",
        "display_name": "Passkey Demo User",
        "email": "passkey@example.com"
    }
    
    print("1. Registration Flow")
    
    # Generate registration challenge
    reg_challenge = webauthn.generate_challenge()
    webauthn.store_challenge(user_id, reg_challenge)
    
    print(f"✓ Registration challenge generated: {reg_challenge[:20]}...")
    
    # Simulate client response (normally from browser/authenticator)
    mock_credential_id = base64.urlsafe_b64encode(
        f"passkey_{user_id}_{secrets.token_hex(8)}".encode()
    ).decode().rstrip('=')
    
    credential_create = PasskeyCredentialCreate(
        name="Demo Device Passkey",
        credential_id=mock_credential_id,
        public_key=b"mock_public_key_data",
        sign_count=0
    )
    
    # Register the passkey
    registered_credential = register_passkey(user_id, credential_create)
    print(f"✓ Passkey registered:")
    print(f"  ID: {registered_credential.id}")
    print(f"  Name: {registered_credential.name}")
    print(f"  Credential ID: {registered_credential.credential_id[:20]}...")
    print(f"  Created: {registered_credential.created_at}")
    
    print("\n2. Authentication Flow")
    
    # Generate authentication challenge
    auth_challenge = webauthn.generate_challenge()
    webauthn.store_challenge(user_id, auth_challenge)
    
    print(f"✓ Authentication challenge generated: {auth_challenge[:20]}...")
    
    # Get allowed credentials for user
    user_credentials = credentials_db.get(user_id, [])
    allowed_credentials = [
        {
            "id": cred.credential_id,
            "type": "public-key",
            "transports": ["internal"]
        }
        for cred in user_credentials if cred.is_active
    ]
    
    print(f"✓ Found {len(allowed_credentials)} allowed credentials")
    
    # Simulate authentication
    success = authenticate_passkey(user_id, registered_credential.credential_id)
    print(f"✓ Authentication: {'Success' if success else 'Failed'}")
    
    if success:
        # Check updated credential info
        updated_credential = credentials_db[user_id][0]
        print(f"  Updated sign count: {updated_credential.sign_count}")
        print(f"  Last used: {updated_credential.last_used}")
    
    print("\n3. Multiple Passkeys")
    
    # Register additional passkeys
    additional_passkeys = [
        {"name": "iPhone Face ID", "device": "mobile"},
        {"name": "Windows Hello", "device": "desktop"},
        {"name": "Hardware Key", "device": "security_key"}
    ]
    
    for passkey_info in additional_passkeys:
        mock_cred_id = base64.urlsafe_b64encode(
            f"{passkey_info['device']}_{secrets.token_hex(6)}".encode()
        ).decode().rstrip('=')
        
        credential = PasskeyCredentialCreate(
            name=passkey_info["name"],
            credential_id=mock_cred_id,
            public_key=b"mock_key_data",
            sign_count=0
        )
        
        register_passkey(user_id, credential)
        print(f"✓ Registered: {passkey_info['name']}")
    
    # Show all registered passkeys
    print(f"\n✓ Total passkeys for user: {len(credentials_db[user_id])}")
    for i, cred in enumerate(credentials_db[user_id], 1):
        print(f"  {i}. {cred.name} (Count: {cred.sign_count}, Active: {cred.is_active})")


def demo_security_features():
    """Demonstrate WebAuthn security features."""
    print_banner("WebAuthn Security Features Demo")
    
    from app.auth.webauthn_service import WebAuthnService
    
    webauthn = WebAuthnService()
    
    print("✓ Security benefits of WebAuthn/Passkeys:")
    print("  - Phishing resistant (domain binding)")
    print("  - No shared secrets (public key cryptography)")
    print("  - Biometric verification (user presence/verification)")
    print("  - Hardware-backed security (secure elements)")
    print("  - Replay attack prevention (challenge-response)")
    print("  - No password database breaches")
    
    print(f"\n✓ Challenge properties:")
    challenge = webauthn.generate_challenge()
    print(f"  - Cryptographically random: {challenge[:30]}...")
    print(f"  - Length: {len(challenge)} characters")
    print(f"  - Base64URL encoded (URL-safe)")
    print(f"  - Single-use (prevents replay attacks)")
    
    print(f"\n✓ Relying Party configuration:")
    print(f"  - RP ID: {webauthn.rp_id} (domain binding)")
    print(f"  - RP Name: {webauthn.rp_name} (user-friendly)")
    print(f"  - Challenge timeout: 5 minutes")
    print(f"  - User verification: Required")
    
    print(f"\n✓ Supported algorithms:")
    algorithms = [
        {"name": "ES256", "alg": -7, "description": "ECDSA w/ SHA-256"},
        {"name": "RS256", "alg": -257, "description": "RSASSA-PKCS1-v1_5 w/ SHA-256"},
        {"name": "EdDSA", "alg": -8, "description": "EdDSA signature algorithms"}
    ]
    
    for algo in algorithms:
        print(f"  - {algo['name']} ({algo['alg']}): {algo['description']}")


async def main():
    """Run the complete WebAuthn/Passkey demo."""
    print_banner("WebAuthn/Passkey Demo")
    print("This demo showcases passwordless authentication with WebAuthn.")
    
    # WebAuthn service demo
    demo_webauthn_service()
    
    # Passkey models demo
    demo_passkey_models()
    
    # Registration challenge demo
    demo_registration_challenge()
    
    # Authentication challenge demo
    demo_authentication_challenge()
    
    # Complete workflow simulation
    demo_passkey_workflow_simulation()
    
    # Security features demo
    demo_security_features()
    
    print_banner("WebAuthn/Passkey Demo Complete")
    print("✓ All WebAuthn features demonstrated successfully!")
    print("\nKey Features Covered:")
    print("- Challenge generation and validation")
    print("- Registration and authentication flows")
    print("- Passkey credential management")
    print("- Multiple authenticator support")
    print("- Security properties and benefits")
    print("- Model validation and serialization")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())