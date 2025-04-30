from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ParliamentTVCaptureRequest(BaseModel):
    """Schema for Parliament TV capture requests."""
    url: str = Field(..., description="Parliament TV event URL")
    title: str = Field(..., description="Title for the capture session")
    description: Optional[str] = Field(None, description="Optional description")
    duration: Optional[int] = Field(300, description="Maximum duration to capture in seconds")
    enable_facial_recognition: Optional[bool] = Field(True, description="Enable facial recognition to stop when speaker is no longer present")
    scheduled_start: Optional[datetime] = Field(None, description="Optional scheduled start time")
    scheduled_end: Optional[datetime] = Field(None, description="Optional scheduled end time")


class ParliamentTVCaptureResponse(BaseModel):
    """Schema for Parliament TV capture responses."""
    id: int
    title: str
    status: str
    url: str
    duration: Optional[int] = None
    facial_recognition_enabled: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    created_by_id: int
    created_by: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
