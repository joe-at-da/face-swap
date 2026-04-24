-- Parliament Video Processing Pipeline Storage Schema
-- This migration creates tables to store complete processing pipeline output
-- for full traceability, debugging, and manual MP identification workflow

-- =====================================================
-- TABLE 1: event_processing_runs
-- Stores metadata for each processing attempt with flattened timing and stats
-- =====================================================
CREATE TABLE IF NOT EXISTS event_processing_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT NOT NULL,
  results_url TEXT NOT NULL,
  video_path TEXT,
  audio_path TEXT,
  processing_version TEXT,
  
  -- Timing (flattened from timing object)
  timing_download_seconds DECIMAL,
  timing_diarization_seconds DECIMAL,
  timing_transcription_seconds DECIMAL,
  timing_asd_seconds DECIMAL,
  timing_mp_identification_seconds DECIMAL,
  timing_clip_creation_seconds DECIMAL,
  timing_total_seconds DECIMAL,
  
  -- Stats - Diarization
  stats_diarization_num_segments INT,
  stats_diarization_duration_seconds DECIMAL,
  
  -- Stats - Transcription
  stats_transcription_transcribed INT,
  stats_transcription_empty INT,
  stats_transcription_hallucination_filtered INT,
  stats_transcription_total_duration DECIMAL,
  stats_transcription_avg_duration DECIMAL,
  
  -- Stats - ASD (Active Speaker Detection)
  stats_asd_total_segments INT,
  stats_asd_with_faces INT,
  stats_asd_skipped_too_short INT,
  stats_asd_skipped_no_faces_selected INT,
  stats_asd_skipped_no_quality_faces INT,
  
  -- Stats - MP Identification
  stats_mp_id_identified INT,
  stats_mp_id_unidentified INT,
  stats_mp_id_unique_speakers INT,
  stats_mp_id_identified_speakers INT,
  stats_mp_id_unidentified_speakers INT,
  stats_mp_id_avg_similarity DECIMAL,
  stats_mp_id_similarity_count INT,
  
  -- Stats - Clip Creation
  stats_clip_horizontal_ok INT,
  stats_clip_vertical_ok INT,
  stats_clip_thumbnails_ok INT,
  stats_clip_horizontal_failed INT,
  stats_clip_vertical_failed INT,
  stats_clip_thumbnails_failed INT,
  stats_clip_uploads_successful INT,
  stats_clip_uploads_failed INT,
  stats_clip_segments_input INT,
  stats_clip_segments_output INT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Foreign key to parliament_events
  CONSTRAINT fk_event_processing_runs_event_id 
    FOREIGN KEY (event_id) 
    REFERENCES parliament_events(event_id) 
    ON DELETE CASCADE
);

-- =====================================================
-- TABLE 2: event_processing_segments
-- Stores ALL segments (identified + unidentified) for full traceability
-- =====================================================
CREATE TABLE IF NOT EXISTS event_processing_segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_run_id UUID NOT NULL,
  segment_index INT NOT NULL,
  speaker TEXT,
  member_id INT,
  is_unidentified BOOLEAN DEFAULT FALSE,
  
  -- Timing
  start_seconds DECIMAL,
  end_seconds DECIMAL,
  duration_seconds DECIMAL,
  start_timestamp TEXT,
  end_timestamp TEXT,
  
  -- Content
  transcript TEXT,
  
  -- Merge Meta (flattened)
  merge_was_merged BOOLEAN,
  merge_segment_count INT,
  merge_absorbed_count INT,
  merge_original_segments JSONB,
  merge_absorbed_segments JSONB,
  
  -- Transcription Meta (flattened)
  transcription_language TEXT,
  transcription_avg_logprob DECIMAL,
  transcription_no_speech_prob DECIMAL,
  transcription_compression_ratio DECIMAL,
  transcription_token_count INT,
  transcription_duration DECIMAL,
  transcription_mode TEXT,
  transcription_use_context BOOLEAN,
  transcription_temperature JSONB,
  transcription_raw_segments JSONB,
  
  -- ASD Meta (flattened)
  asd_avg_speaking_score DECIMAL,
  asd_num_frames INT,
  asd_num_tracks INT,
  asd_num_chunks INT,
  asd_selected_track_frames INT,
  asd_num_faces_saved INT,
  asd_best_quality_score DECIMAL,
  asd_best_is_frontal BOOLEAN,
  asd_best_occlusion_score DECIMAL,
  asd_best_face_size INT,
  asd_has_embedding BOOLEAN,
  asd_chunked_decode BOOLEAN,
  
  -- MP ID Meta (flattened)
  mp_id_num_faces INT,
  mp_id_faces_with_embeddings INT,
  mp_id_num_matches INT,
  mp_id_best_similarity DECIMAL,
  mp_id_weighted_vote_score DECIMAL,
  mp_id_raw_vote_score DECIMAL,
  mp_id_unique_mps_matched INT,
  mp_id_match_confidence DECIMAL,
  mp_id_similarity_tier TEXT,
  mp_id_reason TEXT,
  mp_id_threshold_used DECIMAL,
  mp_id_matched_portrait_row_ids JSONB,
  mp_id_top_candidate_portrait_row_ids JSONB,
  mp_id_match_diagnostics JSONB,
  
  -- Clip URLs
  clip_url TEXT,
  vertical_clip_url TEXT,
  thumbnail_url TEXT,
  vertical_thumbnail_url TEXT,
  full_video_url TEXT,
  
  -- Manual Assignment
  manually_assigned_member_id INT,
  manually_assigned_at TIMESTAMPTZ,
  manually_assigned_by UUID,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Foreign Keys
  CONSTRAINT fk_segments_processing_run_id 
    FOREIGN KEY (processing_run_id) 
    REFERENCES event_processing_runs(id) 
    ON DELETE CASCADE,
    
  CONSTRAINT fk_segments_member_id 
    FOREIGN KEY (member_id) 
    REFERENCES parliament_members(member_id) 
    ON DELETE SET NULL,
    
  CONSTRAINT fk_segments_manually_assigned_member_id 
    FOREIGN KEY (manually_assigned_member_id) 
    REFERENCES parliament_members(member_id) 
    ON DELETE SET NULL
);

-- =====================================================
-- TABLE 3: segment_speaker_faces
-- Stores all face images extracted for each segment
-- =====================================================
CREATE TABLE IF NOT EXISTS segment_speaker_faces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  segment_id UUID NOT NULL,
  face_index INT NOT NULL,
  s3_url TEXT,
  quality_score DECIMAL,
  is_frontal BOOLEAN,
  occlusion_score DECIMAL,
  face_size INT,
  confidence DECIMAL,
  frontal_score DECIMAL,
  size_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  CONSTRAINT fk_speaker_faces_segment_id 
    FOREIGN KEY (segment_id) 
    REFERENCES event_processing_segments(id) 
    ON DELETE CASCADE
);

-- =====================================================
-- TABLE 4: segment_portrait_matches
-- Tracks which portrait encodings matched each segment for debugging
-- =====================================================
CREATE TABLE IF NOT EXISTS segment_portrait_matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  segment_id UUID NOT NULL,
  face_encoding_id UUID NOT NULL,
  member_id INT NOT NULL,
  similarity DECIMAL,
  was_selected BOOLEAN DEFAULT FALSE,
  is_top_candidate BOOLEAN DEFAULT FALSE,
  face_index INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  CONSTRAINT fk_portrait_matches_segment_id 
    FOREIGN KEY (segment_id) 
    REFERENCES event_processing_segments(id) 
    ON DELETE CASCADE,
    
  CONSTRAINT fk_portrait_matches_face_encoding_id 
    FOREIGN KEY (face_encoding_id) 
    REFERENCES parliament_member_face_encodings(id) 
    ON DELETE CASCADE,
    
  CONSTRAINT fk_portrait_matches_member_id 
    FOREIGN KEY (member_id) 
    REFERENCES parliament_members(member_id) 
    ON DELETE CASCADE
);

-- =====================================================
-- INDEXES FOR SCALABILITY
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_processing_runs_event_id 
  ON event_processing_runs(event_id);

CREATE INDEX IF NOT EXISTS idx_processing_runs_created_at 
  ON event_processing_runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_segments_run_id 
  ON event_processing_segments(processing_run_id);

CREATE INDEX IF NOT EXISTS idx_segments_member_id 
  ON event_processing_segments(member_id) 
  WHERE member_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_segments_unidentified 
  ON event_processing_segments(processing_run_id) 
  WHERE is_unidentified = true;

CREATE INDEX IF NOT EXISTS idx_segments_manual_assign 
  ON event_processing_segments(manually_assigned_member_id) 
  WHERE manually_assigned_member_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_faces_segment_id 
  ON segment_speaker_faces(segment_id);

CREATE INDEX IF NOT EXISTS idx_matches_segment_id 
  ON segment_portrait_matches(segment_id);

CREATE INDEX IF NOT EXISTS idx_matches_face_encoding_id 
  ON segment_portrait_matches(face_encoding_id);

CREATE INDEX IF NOT EXISTS idx_matches_member_id 
  ON segment_portrait_matches(member_id);

-- =====================================================
-- DROP STATS COLUMNS FROM parliament_events
-- =====================================================

ALTER TABLE parliament_events 
  DROP COLUMN IF EXISTS db_rows_created,
  DROP COLUMN IF EXISTS gpu_processing_time_seconds,
  DROP COLUMN IF EXISTS mp_identification_accuracy_percent,
  DROP COLUMN IF EXISTS segments_found,
  DROP COLUMN IF EXISTS segments_mp_identified,
  DROP COLUMN IF EXISTS segments_transcribed,
  DROP COLUMN IF EXISTS segments_uploaded,
  DROP COLUMN IF EXISTS total_processing_time_seconds,
  DROP COLUMN IF EXISTS video_file_size_mb;

-- =====================================================
-- DROP META/STATS COLUMNS FROM parliament_member_clips
-- =====================================================

ALTER TABLE parliament_member_clips 
  DROP COLUMN IF EXISTS asd_meta,
  DROP COLUMN IF EXISTS audio_quality_score,
  DROP COLUMN IF EXISTS confidence_score,
  DROP COLUMN IF EXISTS debate_topic,
  DROP COLUMN IF EXISTS mp_id_meta,
  DROP COLUMN IF EXISTS speaker_faces;

-- =====================================================
-- ADD COLUMNS TO parliament_member_clips
-- =====================================================

ALTER TABLE parliament_member_clips 
  ADD COLUMN IF NOT EXISTS processing_segment_id UUID;

-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS TO parliament_member_clips
-- =====================================================

DO $$ 
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_parliament_member_clips_session_uid') THEN
    ALTER TABLE parliament_member_clips DROP CONSTRAINT fk_parliament_member_clips_session_uid;
  END IF;
  
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_parliament_member_clips_processing_segment_id') THEN
    ALTER TABLE parliament_member_clips DROP CONSTRAINT fk_parliament_member_clips_processing_segment_id;
  END IF;
END $$;

ALTER TABLE parliament_member_clips 
  ADD CONSTRAINT fk_parliament_member_clips_session_uid 
  FOREIGN KEY (session_uid) 
  REFERENCES parliament_events(event_id) 
  ON DELETE SET NULL;

ALTER TABLE parliament_member_clips 
  ADD CONSTRAINT fk_parliament_member_clips_processing_segment_id 
  FOREIGN KEY (processing_segment_id) 
  REFERENCES event_processing_segments(id) 
  ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_processing_segment_id 
  ON parliament_member_clips(processing_segment_id) 
  WHERE processing_segment_id IS NOT NULL;
