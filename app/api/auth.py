"""Authentication API routes."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Token, User, UserCreate, LoginRequest
from app.auth.security import create_access_token, create_refresh_token
from app.auth.dependencies import get_current_user, get_current_active_user
from app.models.database import get_db_session as get_db
from app.repositories.user_repository import UserRepository
from app.config import config

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    - **email**: User's email address (must be unique)
    - **username**: Username (must be unique)
    - **password**: Password for the account
    - **is_active**: Whether the user account is active (default: true)
    - **is_superuser**: Whether the user has admin privileges (default: false)
    """
    user_repo = UserRepository(db)
    
    try:
        db_user = await user_repo.create(user_data)
        return User.model_validate(db_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with username/email and password to get access token.
    
    - **username**: Username or email address
    - **password**: User's password
    
    Returns access token for authentication.
    """
    user_repo = UserRepository(db)
    user = await user_repo.authenticate(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=config.security.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.access_token_expire_minutes * 60
    }


@router.post("/login/json", response_model=Token)
async def login_user_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with JSON payload (alternative to form-based login).
    
    - **username**: Username or email address
    - **password**: User's password
    
    Returns access token for authentication.
    """
    user_repo = UserRepository(db)
    user = await user_repo.authenticate(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=config.security.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.access_token_expire_minutes * 60
    }


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    Requires authentication token in Authorization header.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh access token.
    
    Requires valid authentication token in Authorization header.
    """
    access_token_expires = timedelta(minutes=config.security.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username, "user_id": current_user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.access_token_expire_minutes * 60
    }