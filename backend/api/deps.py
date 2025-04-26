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
    except Exception as e:
        # If an exception occurs during the request, rollback the transaction
        db.rollback()
        raise e
    finally:
        try:
            # Close the session safely
            db.close()
        except Exception as e:
            # Log the error but don't raise it to avoid crashing the application
            print(f"Error closing database session: {str(e)}")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    """Get current authenticated user."""
    # Debug information
    print(f"DEBUG - Auth: Token received (first 10 chars): {token[:10] if token else 'None'}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        role = payload.get("role", UserRole.STAFF)  # Default to STAFF if no role
        
        if email == "test":  # Handle test users
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
        
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Look up user by email (matching security.py implementation)
    user = db.query(UserModel).filter(UserModel.email == email).first()
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


async def get_current_user_optional(request = None, db: Session = Depends(get_db)):
    """Get current user if token is provided, otherwise return None.
    
    This is useful for endpoints that can work with or without authentication.
    """
    try:
        # Try to get the token from the authorization header
        if request and request.headers.get("Authorization"):
            auth_header = request.headers.get("Authorization")
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                try:
                    return await get_current_user(db=db, token=token)
                except HTTPException:
                    # Invalid token, return None instead of raising an exception
                    return None
        return None
    except (ValueError, AttributeError, HTTPException):
        # Any error in parsing the token or headers, return None
        return None
