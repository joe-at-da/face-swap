from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class VideoClipBase(BaseModel):
    title: str = Field(..., description="Title of the video clip")
    description: Optional[str] = Field(None, description="Description of the video clip")
    source_url: str = Field(..., description="URL of the source video")
    start_time: datetime = Field(..., description="Start time of the clip in the source video")
    end_time: datetime = Field(..., description="End time of the clip in the source video")
    clip_metadata: Optional[Dict] = Field(default={}, description="Additional metadata for the clip")

class VideoClipCreate(VideoClipBase):
    pass

class VideoClipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    clip_metadata: Optional[Dict] = None

class VideoClip(VideoClipBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status: str = Field(..., description="Status of the video clip (processing, ready, failed)")
    storage_path: Optional[str] = None

    class Config:
        from_attributes = True
