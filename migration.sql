-- Add transcription-related columns to capture_sessions table
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS transcription_status VARCHAR(50);
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS transcription_path TEXT;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS transcription_error TEXT;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS transcription_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS transcription_results TEXT;
