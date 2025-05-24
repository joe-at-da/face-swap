from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class VideoClipBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime

class VideoClipCreate(VideoClipBase):
    capture_session_id: int

class VideoClipUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class VideoClipResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    storage_path: Optional[str] = None
    duration: Optional[float] = None
    owner_id: int  # Changed from user_id to owner_id to match database model
    capture_session_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class VideoClipStatus(BaseModel):
    status: str
    progress: Optional[float] = None

    class Config:
        from_attributes = True
