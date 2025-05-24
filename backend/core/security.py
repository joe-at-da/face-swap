from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.models import User as UserModel
from backend.db.models.user import UserRole
from backend.schemas.auth import TokenData
from backend.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    role: str = None
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Include subject (email) and expiration in the token
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Add role information if provided
    if role:
        to_encode["role"] = role
        
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role", UserRole.STAFF)  # Default to STAFF if no role
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(UserModel).filter(UserModel.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def verify_admin_user(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def has_permission(user, allowed_roles: list) -> bool:
    """Check if user has required role."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Ensure user_role is a UserRole enum
    user_role = user.role
    
    # Check if the user's role is in the allowed roles
    if user_role not in allowed_roles:
        # Format the role values for the error message
        role_values = []
        for role in allowed_roles:
            if hasattr(role, 'value'):
                role_values.append(role.value)
            else:
                role_values.append(str(role))
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Required roles: {role_values}"
        )
    
    return True
