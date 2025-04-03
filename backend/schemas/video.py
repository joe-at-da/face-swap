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

class VideoClipResponse(VideoClipBase):
    id: int
    status: str
    storage_path: Optional[str]
    duration: Optional[float]
    user_id: int
    capture_session_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True

class VideoClipStatus(BaseModel):
    status: str
    progress: Optional[float] = None

    class Config:
        from_attributes = True
