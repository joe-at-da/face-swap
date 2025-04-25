from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user,
    verify_admin_user
)
from backend.db.session import get_db
from backend.schemas.auth import User, UserCreate, UserUpdate, Token
from backend.db.models import User as UserModel

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    print(f"Login attempt with username: {form_data.username}")
    
    try:
        # Check if user exists
        user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
        
        if not user:
            print(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            print(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check if user is active
        if not user.is_active:
            print(f"User is inactive: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        print(f"Login successful for user: {form_data.username}")
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create a JWT token with the user's email as the subject and role
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
        role=user.role.value  # Pass the role value as is (now uppercase from the enum)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=User)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: UserModel = Depends(verify_admin_user)
) -> Any:
    """
    Create new user. Only admin users can create new users.
    """
    user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = UserModel(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=user_in.is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """
    Update own user.
    """
    if user_in.email and user_in.email != current_user.email:
        if db.query(UserModel).filter(UserModel.email == user_in.email).first():
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    if user_in.password is not None:
        current_user.hashed_password = get_password_hash(user_in.password)
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.email is not None:
        current_user.email = user_in.email
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/users", response_model=list[User])
async def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(verify_admin_user)
) -> Any:
    """
    Retrieve users. Only admin users can retrieve all users.
    """
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users
