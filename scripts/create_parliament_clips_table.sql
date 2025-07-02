-- SQL definition for parliament_clips table
CREATE TABLE IF NOT EXISTS parliament_clips (
    id SERIAL PRIMARY KEY,
    
    -- Required fields (starred in your requirements)
    member_id INTEGER NOT NULL,
    transcript TEXT NOT NULL,
    full_video_path TEXT NOT NULL,
    session_date DATE NULL,
    session_type TEXT NULL,
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    
    -- Optional fields
    transcript_embedding JSONB NULL, -- Using JSONB for vector storage locally
    clip_url TEXT NULL,
    debate_topic TEXT NULL,
    status TEXT NULL DEFAULT 'pending_review',
    processing_notes TEXT NULL,
    confidence_score NUMERIC(4, 3) NULL,
    audio_quality_score NUMERIC(4, 3) NULL,
    duration_seconds NUMERIC(10, 3) NULL, -- Can be calculated from start/end timestamps
    
    -- Metadata fields
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    last_synced_at TIMESTAMP WITH TIME ZONE NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on member_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_parliament_clips_member_id ON parliament_clips(member_id);

-- Create index on session_date for filtering by date
CREATE INDEX IF NOT EXISTS idx_parliament_clips_session_date ON parliament_clips(session_date);

-- Comment explaining the table structure
COMMENT ON TABLE parliament_clips IS 'Stores clips of parliament members speaking, with transcripts and metadata';
