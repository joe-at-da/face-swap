from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SpeakerIdentificationRequest(BaseModel):
    """Request model for speaker identification."""
    capture_id: int = Field(..., description="ID of the capture session to process")
    threshold: float = Field(0.6, description="Recognition threshold (lower is stricter)")
    update_db: bool = Field(False, description="Update the MP database before processing")

class SpeakerInfo(BaseModel):
    """Information about an identified speaker."""
    name: str
    frames: int
    average_confidence: float
    metadata: Optional[Dict[str, Any]] = None

class TimelineEntry(BaseModel):
    """Timeline entry for speaker appearances."""
    speaker: str
    start_time: float
    end_time: float
    duration: float

class SpeakerIdentificationResults(BaseModel):
    """Results of speaker identification processing."""
    input_file: str
    output_file: str
    speakers: Dict[str, SpeakerInfo]
    timeline: List[TimelineEntry]
    primary_speaker: Optional[str] = None
    frame_count: int
    processed_frames: int
    processing_info: Dict[str, Any]

class SpeakerIdentificationResponse(BaseModel):
    """Response model for speaker identification."""
    id: int
    capture_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    output_file: Optional[str] = None
    threshold: float
