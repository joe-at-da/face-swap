"""
Schemas for facial and voice recognition.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FacialRecognitionRequest(BaseModel):
    """Request schema for facial recognition."""
    video_id: int = Field(..., description="ID of the video to process")
    save_output: bool = Field(True, description="Whether to save the output video")


class FacialRecognitionResponse(BaseModel):
    """Response schema for facial recognition."""
    success: bool = Field(..., description="Whether the facial recognition was successful")
    message: Optional[str] = Field(None, description="Message about the facial recognition process")
    error: Optional[str] = Field(None, description="Error message if the facial recognition failed")
    output_file: Optional[str] = Field(None, description="Path to the output video file")
    results: Optional[Dict[str, Any]] = Field(None, description="Results of the facial recognition")


class SpeakerIdentificationRequest(BaseModel):
    """Request schema for speaker identification."""
    video_id: int = Field(..., description="ID of the video to process")
    save_output: bool = Field(True, description="Whether to save the output video")


class SpeakerIdentificationResponse(BaseModel):
    """Response schema for speaker identification."""
    success: bool = Field(..., description="Whether the speaker identification was successful")
    message: Optional[str] = Field(None, description="Message about the speaker identification process")
    error: Optional[str] = Field(None, description="Error message if the speaker identification failed")
    output_file: Optional[str] = Field(None, description="Path to the output video file")
    results_file: Optional[str] = Field(None, description="Path to the results file")
    results: Optional[Dict[str, Any]] = Field(None, description="Results of the speaker identification")


class TranscriptionRequest(BaseModel):
    """Request schema for audio transcription."""
    audio_id: int = Field(..., description="ID of the audio to process")
    save_output: bool = Field(True, description="Whether to save the output transcript")


class TranscriptionResponse(BaseModel):
    """Response schema for audio transcription."""
    success: bool = Field(..., description="Whether the transcription was successful")
    message: Optional[str] = Field(None, description="Message about the transcription process")
    error: Optional[str] = Field(None, description="Error message if the transcription failed")
    output_file: Optional[str] = Field(None, description="Path to the output transcript file")
    transcript: Optional[str] = Field(None, description="Transcript text")


class VoiceIdentificationRequest(BaseModel):
    """Request schema for voice identification."""
    audio_id: int = Field(..., description="ID of the audio to process")
    save_output: bool = Field(True, description="Whether to save the output audio")


class VoiceIdentificationResponse(BaseModel):
    """Response schema for voice identification."""
    success: bool = Field(..., description="Whether the voice identification was successful")
    message: Optional[str] = Field(None, description="Message about the voice identification process")
    error: Optional[str] = Field(None, description="Error message if the voice identification failed")
    output_file: Optional[str] = Field(None, description="Path to the output audio file")
    results_file: Optional[str] = Field(None, description="Path to the results file")
    results: Optional[Dict[str, Any]] = Field(None, description="Results of the voice identification")


class CombinedRecognitionRequest(BaseModel):
    """Request schema for combined facial and voice recognition."""
    video_id: int = Field(..., description="ID of the video to process")
    save_output: bool = Field(True, description="Whether to save the output files")


class CombinedRecognitionResponse(BaseModel):
    """Response schema for combined facial and voice recognition."""
    success: bool = Field(..., description="Whether the combined recognition was successful")
    message: Optional[str] = Field(None, description="Message about the combined recognition process")
    error: Optional[str] = Field(None, description="Error message if the combined recognition failed")
    video_output_file: Optional[str] = Field(None, description="Path to the output video file")
    audio_output_file: Optional[str] = Field(None, description="Path to the output audio file")
    transcript_file: Optional[str] = Field(None, description="Path to the transcript file")
    results_file: Optional[str] = Field(None, description="Path to the combined results file")
    results: Optional[Dict[str, Any]] = Field(None, description="Results of the combined recognition")


class RecognitionStatus(BaseModel):
    """Basic recognition status information."""
    status: str = Field(..., description="Current status of the recognition process")
    video_id: int = Field(..., description="ID of the video being processed")
    started_at: Optional[datetime] = Field(None, description="When the recognition process started")
    completed_at: Optional[datetime] = Field(None, description="When the recognition process completed")
    has_results: bool = Field(False, description="Whether the recognition has results available")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information if available")


class RecognitionStatusResponse(BaseModel):
    """Response schema for recognition status endpoint."""
    success: bool = Field(..., description="Whether the status request was successful")
    status: RecognitionStatus = Field(..., description="Status information")
    error: Optional[str] = Field(None, description="Error message if the status request failed")


class ProgressStep(BaseModel):
    """Information about a single step in the recognition process."""
    name: str = Field(..., description="Name of the step")
    status: str = Field(..., description="Status of the step (started, completed, error)")
    timestamp: str = Field(..., description="Timestamp when the step status was updated")
    message: Optional[str] = Field(None, description="Message about the step")
    completion_percentage: Optional[float] = Field(None, description="Completion percentage of the step")


class ProgressData(BaseModel):
    """Detailed progress information for the recognition process."""
    status: str = Field(..., description="Overall status of the recognition process")
    completion_percentage: Optional[float] = Field(None, description="Overall completion percentage")
    current_step: Optional[str] = Field(None, description="Current step being processed")
    start_time: Optional[str] = Field(None, description="When the recognition process started")
    last_update: Optional[str] = Field(None, description="When the progress was last updated")
    steps: List[ProgressStep] = Field(default_factory=list, description="List of processing steps")
    completed_at: Optional[str] = Field(None, description="When the recognition process completed")
    error: Optional[str] = Field(None, description="Error message if the recognition failed")
    error_at: Optional[str] = Field(None, description="When the error occurred")


class DetailedRecognitionStatus(BaseModel):
    """Detailed recognition status including progress information."""
    status: str = Field(..., description="Current status of the recognition process")
    video_id: int = Field(..., description="ID of the video being processed")
    started_at: Optional[datetime] = Field(None, description="When the recognition process started")
    completed_at: Optional[datetime] = Field(None, description="When the recognition process completed")
    has_results: bool = Field(False, description="Whether the recognition has results available")
    progress: Optional[ProgressData] = Field(None, description="Detailed progress information")


class DetailedRecognitionStatusResponse(BaseModel):
    """Response schema for detailed recognition status endpoint."""
    success: bool = Field(..., description="Whether the status request was successful")
    status: DetailedRecognitionStatus = Field(..., description="Detailed status information")
    error: Optional[str] = Field(None, description="Error message if the status request failed")
