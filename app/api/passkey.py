"""Passkey authentication API routes."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passkey_models import (
    WebAuthnRegistrationChallenge,
    WebAuthnAuthenticationChallenge,
    WebAuthnRegistrationResponse,
    WebAuthnAuthenticationResponse,
    PasskeyRegistrationRequest,
    PasskeyAuthenticationRequest,
    PasskeyTokenResponse,
    PasskeyCredential,
    PasskeyCredentialCreate
)
from app.auth.models import User
from app.auth.security import create_access_token
from app.auth.dependencies import get_current_active_user
from app.auth.webauthn_service import webauthn_service
from app.models.database import get_db_session as get_db
from app.repositories.user_repository import UserRepository
from app.repositories.passkey_repository import PasskeyCredentialRepository
from app.config import config

router = APIRouter(prefix="/api/v1/passkey", tags=["passkey"])


@router.post("/register/begin", response_model=WebAuthnRegistrationChallenge)
async def begin_passkey_registration(
    request: PasskeyRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Begin passkey registration process.
    
    - **username**: Username of the account to register a passkey for
    
    Returns WebAuthn registration challenge options.
    """
    user_repo = UserRepository(db)
    passkey_repo = PasskeyCredentialRepository(db)
    
    # Find user by username
    user = await user_repo.get_by_username(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # Get existing credentials to exclude
    exclude_credentials = await passkey_repo.get_credential_ids_for_user(user.id)
    
    # Create registration options
    options = webauthn_service.create_registration_options(
        user_id=user.id,
        username=user.username,
        display_name=user.email,
        exclude_credentials=exclude_credentials
    )
    
    return WebAuthnRegistrationChallenge(**options)


@router.post("/register/complete", response_model=PasskeyCredential)
async def complete_passkey_registration(
    response: WebAuthnRegistrationResponse,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete passkey registration process.
    
    Requires authentication. The user must be logged in to register a passkey.
    """
    passkey_repo = PasskeyCredentialRepository(db)
    
    # Verify the registration response
    is_valid, verification_result = webauthn_service.verify_registration_response(
        user_id=current_user.id,
        response=response.model_dump()
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {verification_result.get('error', 'Unknown error')}"
        )
    
    # Create credential record
    credential_data = PasskeyCredentialCreate(
        credential_id=verification_result['credential_id'],
        public_key=verification_result['public_key'],
        sign_count=verification_result['sign_count'],
        name=response.name
    )
    
    try:
        db_credential = await passkey_repo.create(current_user.id, credential_data)
        return PasskeyCredential.model_validate(db_credential)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save credential: {str(e)}"
        )


@router.post("/authenticate/begin", response_model=WebAuthnAuthenticationChallenge)
async def begin_passkey_authentication(
    request: PasskeyAuthenticationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Begin passkey authentication process.
    
    - **username**: Username to authenticate (optional for usernameless flow)
    
    Returns WebAuthn authentication challenge options.
    """
    allow_credentials = []
    user_id = None
    
    if request.username:
        user_repo = UserRepository(db)
        passkey_repo = PasskeyCredentialRepository(db)
        
        # Find user by username
        user = await user_repo.get_by_username(request.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        user_id = user.id
        # Get user's credentials
        allow_credentials = await passkey_repo.get_credential_ids_for_user(user.id)
        
        if not allow_credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No passkey credentials found for this user"
            )
    
    # Create authentication options
    options, challenge = webauthn_service.create_authentication_options(
        user_id=user_id,
        allow_credentials=allow_credentials
    )
    
    # Store challenge in a way that we can retrieve it later
    # In a real application, you might want to store this in Redis with the challenge as key
    if not user_id:
        # For usernameless flow, we need to store the challenge differently
        # For now, we'll include it in the response and expect it back
        options['_challenge'] = challenge
    
    return WebAuthnAuthenticationChallenge(**options)


@router.post("/authenticate/complete", response_model=PasskeyTokenResponse)
async def complete_passkey_authentication(
    response: WebAuthnAuthenticationResponse,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete passkey authentication process.
    
    Returns access token on successful authentication.
    """
    passkey_repo = PasskeyCredentialRepository(db)
    
    # Get credential by ID
    credential = await passkey_repo.get_by_credential_id(response.id)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    if not credential.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # Get stored challenge
    challenge = webauthn_service.get_challenge(credential.user_id)
    if not challenge:
        # Try to get challenge from usernameless flow (this is a simplified approach)
        # In production, implement proper challenge storage
        challenge = response.response.get('challenge')
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No challenge found or challenge expired"
            )
    
    # Verify the authentication response
    is_valid, verification_result = webauthn_service.verify_authentication_response(
        credential_id=credential.credential_id,
        public_key=credential.public_key,
        stored_sign_count=credential.sign_count,
        response=response.model_dump(),
        challenge=challenge
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {verification_result.get('error', 'Unknown error')}"
        )
    
    # Update sign count
    new_sign_count = verification_result['sign_count']
    await passkey_repo.update_sign_count(credential.credential_id, new_sign_count)
    
    # Clear challenge
    webauthn_service.clear_challenge(credential.user_id)
    
    # Create access token
    access_token_expires = timedelta(minutes=config.security.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": credential.user.username, "user_id": credential.user_id},
        expires_delta=access_token_expires
    )
    
    return PasskeyTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=config.security.access_token_expire_minutes * 60,
        user={
            "id": credential.user_id,
            "username": credential.user.username,
            "email": credential.user.email,
            "is_active": credential.user.is_active,
            "is_superuser": credential.user.is_superuser
        }
    )


@router.get("/credentials", response_model=list[PasskeyCredential])
async def list_user_passkeys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all passkey credentials for the current user.
    
    Requires authentication.
    """
    passkey_repo = PasskeyCredentialRepository(db)
    credentials = await passkey_repo.get_by_user_id(current_user.id)
    
    return [PasskeyCredential.model_validate(cred) for cred in credentials]


@router.delete("/credentials/{credential_id}")
async def delete_passkey_credential(
    credential_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a passkey credential.
    
    Requires authentication. Users can only delete their own credentials.
    """
    passkey_repo = PasskeyCredentialRepository(db)
    
    success = await passkey_repo.delete(credential_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or not owned by user"
        )
    
    return {"message": "Credential deleted successfully"}