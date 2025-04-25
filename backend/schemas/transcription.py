from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TranscriptionSegment(BaseModel):
    """A segment of transcribed text with timestamps."""
    id: int
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")

class TranscriptionBase(BaseModel):
    """Base transcription model."""
    text: str = Field(..., description="Full transcribed text")
    language: str = Field(..., description="Language code of the transcription")
    segments: List[TranscriptionSegment] = Field(..., description="Segments with timestamps")

class TranscriptionCreate(BaseModel):
    """Model for creating a new transcription request."""
    video_clip_id: int = Field(..., description="ID of the video clip to transcribe")
    language: str = Field("en", description="Language code for transcription")

class TranscriptionResponse(TranscriptionBase):
    """Response model for transcription data."""
    id: int
    video_clip_id: int
    created_at: datetime
    status: str = Field(..., description="Status of the transcription (processing, ready, failed)")
    
    class Config:
        from_attributes = True

class TranscriptionSearch(BaseModel):
    """Model for searching within transcriptions."""
    query: str = Field(..., description="Search query")
    video_clip_id: Optional[int] = Field(None, description="Optional video clip ID to search within")

class TranscriptionSearchResult(BaseModel):
    """Result of a transcription search."""
    video_clip_id: int
    clip_title: str
    matches: List[TranscriptionSegment]
    
    class Config:
        from_attributes = True
