from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from backend.api import deps
from backend.db.models.user import User, UserRole
from backend.schemas.auth import UserCreate, UserUpdate, User as UserResponse
from backend.schemas.admin import SystemStats
from pydantic import BaseModel
from backend.core.security import get_password_hash

router = APIRouter()

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get system statistics for the admin dashboard.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Get user stats
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.is_active == False).scalar() or 0
        
        # Return hardcoded stats for now to get the endpoint working
        return {
            "storage": {
                "total": 1000000000000,  # 1 TB
                "used": 250000000000,   # 250 GB
                "available": 750000000000  # 750 GB
            },
            "clips": {
                "total": 100,
                "processing": 5,
                "completed": 90,
                "failed": 5
            },
            "captures": {
                "total": 50,
                "active": 2,
                "completed": 45,
                "failed": 3
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users
            },
            "social": {
                "total_posts": 75,
                "scheduled_posts": 10,
                "published_posts": 65
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system stats: {str(e)}"
        )


class StorageSettings(BaseModel):
    max_file_size: int
    allowed_extensions: list[str]
    auto_delete_days: int
    storage_path: str


class StorageStats(BaseModel):
    total_space: int
    used_space: int
    free_space: int
    file_count: int
    average_file_size: int


@router.get("/storage/stats", response_model=StorageStats)
async def get_storage_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get storage statistics.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Return hardcoded storage stats for now
    return {
        "total_space": 1000000000000,  # 1 TB
        "used_space": 250000000000,   # 250 GB
        "free_space": 750000000000,  # 750 GB
        "file_count": 1250,
        "average_file_size": 200000000  # 200 MB
    }


@router.get("/storage/settings", response_model=StorageSettings)
async def get_storage_settings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get storage settings.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Return hardcoded storage settings for now
    return {
        "max_file_size": 5000000000,  # 5 GB
        "allowed_extensions": ["mp4", "mov", "avi", "mkv"],
        "auto_delete_days": 30,
        "storage_path": "/data/videos"
    }


@router.put("/storage/settings", response_model=StorageSettings)
async def update_storage_settings(
    settings: StorageSettings,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update storage settings.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # In a real implementation, we would update the settings in the database
    # For now, just return the settings that were sent
    return settings


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Retrieve all users with optional filtering.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    query = db.query(User)
    
    # Apply filters if provided
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            User.email.ilike(search_term) | 
            User.full_name.ilike(search_term)
        )
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/users", response_model=UserResponse)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Create new user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Check if user with this email already exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get a specific user by id.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update a user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update user fields
    update_data = user_in.dict(exclude_unset=True)
    
    # If password is being updated, hash it
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"]
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Delete a user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Prevent deleting self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    db.delete(user)
    db.commit()
    return user


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update a user's active status.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Prevent deactivating self
    if user_id == current_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
