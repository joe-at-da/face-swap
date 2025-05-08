-- SQL script to add recognition columns to the capture_sessions table
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_progress TEXT;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_status VARCHAR(50);
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS recognition_results TEXT;
