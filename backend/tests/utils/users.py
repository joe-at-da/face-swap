from datetime import datetime, timedelta
from jose import jwt
from backend.db import models
from backend.core.config import settings

def create_test_user(role: str = "USER", db = None) -> models.User:
    """Create a test user with the given role."""
    user = models.User(
        email=f"test_{role.lower()}@example.com",
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
            "sub": str(user.id),
            "exp": expire,
            "role": user.role
        }
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    user.create_token = create_token
    return user
