from datetime import datetime, timedelta
import uuid
from jose import jwt
from backend.db import models
from backend.db.models.user import UserRole
from backend.core.config import settings

def create_test_user(role: str = "staff", db = None) -> models.User:
    """Create a test user with the given role."""
    # Convert string role to UserRole enum
    if isinstance(role, str):
        # Handle both uppercase and lowercase role names
        role = role.lower()
        try:
            role = UserRole(role)
        except ValueError:
            # Default to STAFF if invalid role
            role = UserRole.STAFF
    
    suffix = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for uniqueness
    user = models.User(
        email=f"test_{role.value}_{suffix}@example.com",
        hashed_password="hashed_test_password",
        role=role,
        is_active=True
    )
    if db:
        db.add(user)
        db.commit()
        db.refresh(user)
    
    def create_token():
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        data = {
            "sub": str(user.id) if user.id else "test",  # Use "test" for non-db users
            "exp": expire,
            "role": user.role
        }
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    user.create_token = create_token
    return user
