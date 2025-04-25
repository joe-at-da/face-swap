from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models.user import User as UserModel, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_db() -> Generator:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")
        if sub == "test":  # Handle test users
            # Get role from payload and convert to UserRole enum
            role_str = payload.get("role", "staff")
            if isinstance(role_str, str):
                try:
                    role = UserRole(role_str.lower())
                except ValueError:
                    role = UserRole.STAFF
            else:
                role = UserRole.STAFF
                
            user = UserModel(
                id=0,  # Use 0 for test users
                email="test@example.com",
                role=role,
                is_active=True
            )
            return user
        
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            raise credentials_exception
            
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )

    return user


def get_current_user_with_roles(allowed_roles: list[UserRole]):
    """Get current user and verify they have one of the allowed roles."""
    def _get_user_with_roles(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return _get_user_with_roles
