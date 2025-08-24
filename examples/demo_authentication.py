#!/usr/bin/env python3
"""
Demo script showcasing Authentication & JWT features.

This demo demonstrates:
- Password hashing and verification
- JWT token creation and validation
- User registration and login flow simulation
- Protected endpoint access patterns
- Token expiration handling
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def demo_password_hashing():
    """Demonstrate password hashing and verification."""
    print_banner("Password Hashing Demo")
    
    from app.auth.security import pwd_context
    
    # Test passwords
    passwords = ["mySecretPassword123!", "admin2024", "user@pass"]
    
    for password in passwords:
        # Hash password
        hashed = pwd_context.hash(password)
        print(f"✓ Password: {password}")
        print(f"  Hashed: {hashed[:50]}...")
        
        # Verify password
        is_valid = pwd_context.verify(password, hashed)
        print(f"  Verification: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        # Test wrong password
        is_invalid = pwd_context.verify("wrongpassword", hashed)
        print(f"  Wrong password: {'✗ Incorrectly Valid' if is_invalid else '✓ Correctly Invalid'}")
        print()


def demo_jwt_tokens():
    """Demonstrate JWT token creation and validation."""
    print_banner("JWT Token Demo")
    
    from app.auth.security import create_access_token, verify_token
    
    # Create tokens for different users
    users = [
        {"user_id": 1, "username": "admin", "email": "admin@example.com"},
        {"user_id": 2, "username": "user1", "email": "user1@example.com"},
        {"user_id": 3, "username": "demo", "email": "demo@example.com"},
    ]
    
    for user_data in users:
        print(f"Creating token for user: {user_data['username']}")
        
        # Create access token
        token = create_access_token(data={"sub": user_data["username"], **user_data})
        print(f"✓ Token created: {token[:50]}...")
        
        # Verify token
        payload = verify_token(token)
        if payload:
            print(f"✓ Token verified successfully")
            print(f"  User ID: {payload.get('user_id')}")
            print(f"  Username: {payload.get('username')}")
            print(f"  Email: {payload.get('email')}")
            exp_time = datetime.fromtimestamp(payload.get('exp', 0), tz=timezone.utc)
            print(f"  Expires: {exp_time}")
        else:
            print("✗ Token verification failed")
        print()


def demo_token_expiration():
    """Demonstrate token expiration handling."""
    print_banner("Token Expiration Demo")
    
    from app.auth.security import create_access_token, verify_token
    
    # Create a short-lived token (1 second)
    short_token = create_access_token(
        data={"sub": "testuser", "user_id": 999},
        expires_delta=timedelta(seconds=1)
    )
    
    print("Created short-lived token (1 second expiration)")
    print(f"Token: {short_token[:50]}...")
    
    # Verify immediately
    payload = verify_token(short_token)
    print(f"✓ Immediate verification: {'Success' if payload else 'Failed'}")
    
    # Wait for expiration
    print("Waiting 2 seconds for token to expire...")
    import time
    time.sleep(2)
    
    # Verify after expiration
    payload = verify_token(short_token)
    print(f"✓ After expiration: {'Failed (as expected)' if not payload else 'Unexpectedly valid'}")


def demo_user_models():
    """Demonstrate user model validation and serialization."""
    print_banner("User Models Demo")
    
    from app.auth.models import UserCreate, UserUpdate, User, Token
    from pydantic import ValidationError
    
    # Valid user creation
    try:
        user_create = UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="securePassword123!"
        )
        print(f"✓ Valid user creation:")
        print(f"  Email: {user_create.email}")
        print(f"  Username: {user_create.username}")
        print(f"  Is Active: {user_create.is_active}")
        print(f"  Is Superuser: {user_create.is_superuser}")
    except ValidationError as e:
        print(f"✗ User creation failed: {e}")
    
    # Invalid email validation
    try:
        invalid_user = UserCreate(
            email="not-an-email",
            username="user2",
            password="pass123"
        )
        print("✗ Invalid email validation failed")
    except ValidationError as e:
        print("✓ Invalid email correctly rejected")
        print(f"  Error: {e.errors()[0]['msg']}")
    
    # User update model
    user_update = UserUpdate(email="updated@example.com", is_active=False)
    print(f"\n✓ User update model:")
    print(f"  Fields to update: {user_update.model_dump(exclude_unset=True)}")
    
    # Token model
    token = Token(access_token="sample-jwt-token", token_type="bearer", expires_in=1800)
    print(f"\n✓ Token model:")
    print(f"  Access Token: {token.access_token}")
    print(f"  Token Type: {token.token_type}")
    print(f"  Expires In: {token.expires_in} seconds")


def demo_auth_simulation():
    """Simulate a complete authentication flow."""
    print_banner("Authentication Flow Simulation")
    
    from app.auth.security import pwd_context, create_access_token, verify_token
    from app.auth.models import UserCreate, User, Token
    
    # Simulate user database
    users_db: Dict[str, Dict[str, Any]] = {}
    
    def register_user(user_data: UserCreate) -> User:
        """Simulate user registration."""
        if user_data.username in users_db:
            raise ValueError("Username already exists")
        
        # Hash password
        hashed_password = pwd_context.hash(user_data.password)
        
        # Store user
        user_record = {
            "id": len(users_db) + 1,
            "email": user_data.email,
            "username": user_data.username,
            "hashed_password": hashed_password,
            "is_active": user_data.is_active,
            "is_superuser": user_data.is_superuser,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        users_db[user_data.username] = user_record
        
        return User(**{k: v for k, v in user_record.items() if k != "hashed_password"})
    
    def authenticate_user(username: str, password: str) -> Token:
        """Simulate user authentication."""
        if username not in users_db:
            raise ValueError("User not found")
        
        user = users_db[username]
        if not pwd_context.verify(password, user["hashed_password"]):
            raise ValueError("Invalid password")
        
        if not user["is_active"]:
            raise ValueError("User account is disabled")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": username, "user_id": user["id"]}
        )
        
        return Token(access_token=access_token, token_type="bearer", expires_in=1800)
    
    def get_current_user(token: str) -> User:
        """Simulate getting current user from token."""
        payload = verify_token(token)
        if not payload:
            raise ValueError("Invalid token")
        
        username = payload.get("sub")
        if not username or username not in users_db:
            raise ValueError("User not found")
        
        user = users_db[username]
        return User(**{k: v for k, v in user.items() if k != "hashed_password"})
    
    # Demo the flow
    print("1. User Registration")
    try:
        user_create = UserCreate(
            email="demo@example.com",
            username="demouser",
            password="demoPassword123!"
        )
        registered_user = register_user(user_create)
        print(f"✓ User registered: {registered_user.username} (ID: {registered_user.id})")
    except Exception as e:
        print(f"✗ Registration failed: {e}")
    
    print("\n2. User Login")
    try:
        token = authenticate_user("demouser", "demoPassword123!")
        print(f"✓ Login successful")
        print(f"  Token: {token.access_token[:50]}...")
        print(f"  Type: {token.token_type}")
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return
    
    print("\n3. Protected Resource Access")
    try:
        current_user = get_current_user(token.access_token)
        print(f"✓ Access granted to protected resource")
        print(f"  User: {current_user.username}")
        print(f"  Email: {current_user.email}")
        print(f"  Active: {current_user.is_active}")
    except Exception as e:
        print(f"✗ Access denied: {e}")
    
    print("\n4. Invalid Login Attempt")
    try:
        authenticate_user("demouser", "wrongpassword")
        print("✗ Invalid login attempt succeeded (should fail)")
    except Exception as e:
        print(f"✓ Invalid login correctly rejected: {e}")
    
    print("\n5. Database State")
    print(f"Total users registered: {len(users_db)}")
    for username, user_data in users_db.items():
        print(f"  - {username}: {user_data['email']} (Active: {user_data['is_active']})")


async def main():
    """Run the complete authentication demo."""
    print_banner("Authentication & JWT Demo")
    print("This demo showcases password hashing, JWT tokens, and auth flows.")
    
    # Password hashing demo
    demo_password_hashing()
    
    # JWT token demo
    demo_jwt_tokens()
    
    # Token expiration demo
    demo_token_expiration()
    
    # User models demo
    demo_user_models()
    
    # Complete auth flow simulation
    demo_auth_simulation()
    
    print_banner("Authentication Demo Complete")
    print("✓ All authentication features demonstrated successfully!")
    print("\nKey Features Covered:")
    print("- Password hashing with bcrypt")
    print("- JWT token creation and validation")
    print("- Token expiration handling")
    print("- User model validation")
    print("- Complete registration/login flow")
    print("- Protected resource access")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())