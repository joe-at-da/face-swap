/**
 * TypeScript interfaces for RunPod API integration
 * Supports three serverless endpoints: Video Processor, Clip Creator, and Face Encoder
 */

// =============================================================================
// 1. Video Processor (Parliament Events)
// =============================================================================

export interface VideoProcessorInput {
  parliament_event_id: string; // UUID from parliament_events table
}

export interface VideoProcessorSegment {
  speaker: string;
  start_time: number;
  end_time: number;
  duration: number;
  original_speaker_id: string;
  transcript: string;
  member_id?: number;
  clip_url?: string;
  vertical_clip_url?: string;
  thumbnail_url?: string;
  vertical_thumbnail_url?: string;
  db_record_id?: string;
}

export interface VideoProcessorStep {
  step: string;
  status: string;
  duration_seconds: number;
  details: Record<string, unknown>;
}

export interface VideoProcessorSummary {
  total_segments: number;
  mps_identified: number;
  mps_identified_percentage: number;
  transcripts_generated: number;
  clips_uploaded: number;
  db_records_created: number;
  unique_speakers: number;
  processing_time_minutes: number;
  full_video_uploaded: boolean;
  unidentified_clips_count: number;
}

export interface VideoProcessorResponse {
  status: boolean;
  parliament_event_id?: string;
  session_uid: string;
  file_size_mb: number;
  total_time_seconds: number;
  processing_speed: string;
  timestamp: string;
  summary: VideoProcessorSummary;
  segments: VideoProcessorSegment[];
  full_video_url?: string;
  full_video_s3_path?: string;
  clips_uploaded: number;
  clips_s3_paths: string[];
  s3_bucket: string;
  s3_endpoint: string;
  steps: VideoProcessorStep[];
  error?: string;
}

// =============================================================================
// 2. Clip Creator (User Clips)
// =============================================================================

export interface ClipCreatorInput {
  user_clip_id: string; // UUID from user_clips table
}

export interface ClipCreatorOutputs {
  horizontal_clip_url?: string;
  vertical_clip_url?: string;
  horizontal_thumbnail_url?: string;
  vertical_thumbnail_url?: string;
}

export interface ClipCreatorProcessingTime {
  validation: number;
  user_clips_query?: number;
  clip_creation: number;
  upload: number;
  transcript?: number;
  total: number;
}

export interface GpuInfo {
  available: boolean;
  name: string;
  memory_gb: string;
}

export interface ClipCreatorResponse {
  status: boolean;
  job_id: string;
  user_clip_id?: string;
  userId: string;
  workflow_type: "user_clips";
  outputs: ClipCreatorOutputs;
  transcript?: string;
  processing_time: ClipCreatorProcessingTime;
  gpu_info: GpuInfo;
  error?: string;
}

// =============================================================================
// 3. Face Encoder
// =============================================================================

// Queue-based input for face encoder
export interface FaceEncoderInput {
  detection_threshold?: number; // Default: 0.65
  batch_size?: number;          // Default: auto-detected based on GPU
  max_workers?: number;         // Default: auto-detected based on CPU
  target_portraits?: number;    // Optional: limit number of portraits to process
}

export interface FaceEncoderProcessingSummary {
  total_portraits: number;
  portraits_without_encodings: number;
  portraits_processed: number;
  encodings_created: number;
  encodings_failed: number;
  batch_count: number;
  avg_time_per_portrait: number;
  portraits_per_minute: number;
}

export interface FaceEncoderGpuInfo {
  name: string;
  memory_gb: number;
  cuda_available: boolean;
}

export interface FaceEncoderCpuInfo {
  count: number;
  effective_count: number;
}

export interface FaceEncoderProcessingTime {
  query_portraits: number;
  face_encoding: number;
  database_storage: number;
  cleanup: number;
  total: number;
}

export interface FaceEncoderResponse {
  status: boolean;
  job_id: string;
  total_time_seconds: number;
  processing_summary: FaceEncoderProcessingSummary;
  gpu_info: FaceEncoderGpuInfo;
  cpu_info: FaceEncoderCpuInfo;
  processing_time: FaceEncoderProcessingTime;
  error?: string;
}

// =============================================================================
// RunPod Configuration and Client Types
// =============================================================================

export interface RunPodConfig {
  videoProcessorEndpoint: string;
  clipCreatorEndpoint: string;
  faceEncoderEndpoint: string;
  apiKey: string;
}


export interface RunPodApiRequest<T = unknown> {
  input: T;
}

export interface RunPodApiError {
  error: string;
  details?: unknown;
  statusCode?: number;
}

// Generic RunPod response wrapper (what the API actually returns)
export interface RunPodApiResponse<T = unknown> {
  id: string;
  status: "COMPLETED" | "FAILED" | "IN_PROGRESS" | "IN_QUEUE";
  output?: T;
  error?: string;
}

// Service method response types
export type VideoProcessorResult = VideoProcessorResponse | RunPodApiError;
export type ClipCreatorResult = ClipCreatorResponse | RunPodApiError;
export type FaceEncoderResult = FaceEncoderResponse | RunPodApiError;

// API Route request/response types
export interface ProcessVideoRequest {
  parliament_event_id: string;
}

export interface CreateClipRequest {
  user_clip_id: string;
}

export interface EncodeFacesRequest {
  batch_size?: number;
  max_workers?: number;
  target_portraits?: number;
}

// Standard API response format
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}