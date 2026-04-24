-- UK Parliament Member Clips Table
-- Migration to store video clips with transcripts and embeddings
-- This table tracks individual clips from parliament sessions with members speaking

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for storing transcript embeddings
CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;

-- Create enum for clip status
CREATE TYPE parliament_clip_status AS ENUM (
    'processing', 
    'completed', 
    'failed',
    'pending_review'
);

-- Parliament member clips table
CREATE TABLE parliament_member_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to parliament member
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
    
    -- Clip timing information
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds DECIMAL(10,3) GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_timestamp - start_timestamp))
    ) STORED,
    
    -- Transcript and content
    transcript TEXT NOT NULL,
    transcript_embedding vector(1536), -- OpenAI text-embedding-3-small dimension (1536 < 2000 limit)
    
    -- Media file information
    clip_url TEXT,
    full_video_path TEXT NOT NULL,
    
    -- Additional metadata
    session_date DATE,
    session_type TEXT, -- e.g., 'Commons', 'Lords', 'Committee'
    debate_topic TEXT,
    
    -- Processing status
    status parliament_clip_status DEFAULT 'pending_review',
    processing_notes TEXT,
    
    -- Quality metrics
    confidence_score DECIMAL(4,3), -- 0.000 to 1.000
    audio_quality_score DECIMAL(4,3), -- 0.000 to 1.000
    
    -- Soft deletion support
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_timestamp_order CHECK (start_timestamp < end_timestamp),
    CONSTRAINT valid_duration CHECK (duration_seconds > 0),
    CONSTRAINT valid_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT valid_audio_quality_score CHECK (audio_quality_score >= 0 AND audio_quality_score <= 1)
);

-- Create indexes for better query performance
CREATE INDEX idx_parliament_member_clips_member_id ON parliament_member_clips(member_id);
CREATE INDEX idx_parliament_member_clips_session_date ON parliament_member_clips(session_date);
CREATE INDEX idx_parliament_member_clips_start_timestamp ON parliament_member_clips(start_timestamp);
CREATE INDEX idx_parliament_member_clips_end_timestamp ON parliament_member_clips(end_timestamp);
CREATE INDEX idx_parliament_member_clips_status ON parliament_member_clips(status);
CREATE INDEX idx_parliament_member_clips_active ON parliament_member_clips(member_id, is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_parliament_member_clips_session_type ON parliament_member_clips(session_type);
CREATE INDEX idx_parliament_member_clips_last_synced ON parliament_member_clips(last_synced_at);

-- Create HNSW index for vector similarity search on transcript embeddings
CREATE INDEX idx_parliament_member_clips_transcript_embedding_hnsw 
ON parliament_member_clips 
USING hnsw (transcript_embedding vector_cosine_ops);

-- Create GIN index for full-text search on transcript
CREATE INDEX idx_parliament_member_clips_transcript_gin 
ON parliament_member_clips 
USING gin (to_tsvector('english', transcript));

-- Create composite index for common queries (member + date + status)
CREATE INDEX idx_parliament_member_clips_member_date_status 
ON parliament_member_clips(member_id, session_date, status) 
WHERE is_deleted = FALSE;

-- Create updated_at trigger
CREATE TRIGGER update_parliament_member_clips_updated_at 
    BEFORE UPDATE ON parliament_member_clips 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE parliament_member_clips ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for authenticated users
CREATE POLICY "Parliament member clips are viewable by authenticated users" 
ON parliament_member_clips
FOR SELECT 
USING (auth.role() = 'authenticated');

-- Create RLS policy for admins to manage clips
CREATE POLICY "Allow authenticated users to insert clips" 
ON parliament_member_clips
FOR INSERT 
TO authenticated
WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update clips" 
ON parliament_member_clips
FOR UPDATE 
TO authenticated
USING (true)
WITH CHECK (true);

-- Grant permissions for service role (for cron jobs and API operations)
GRANT ALL ON parliament_member_clips TO service_role;

-- Grant permissions for authenticated users
GRANT SELECT, INSERT, UPDATE ON parliament_member_clips TO authenticated;

-- Add table and column comments for documentation
COMMENT ON TABLE parliament_member_clips IS 
'Stores video clips of parliament members speaking with transcripts and embeddings for semantic search';

COMMENT ON COLUMN parliament_member_clips.member_id IS 
'Reference to parliament_members.member_id';

COMMENT ON COLUMN parliament_member_clips.start_timestamp IS 
'When the member started speaking in this clip';

COMMENT ON COLUMN parliament_member_clips.end_timestamp IS 
'When the member finished speaking in this clip';

COMMENT ON COLUMN parliament_member_clips.duration_seconds IS 
'Calculated duration of the clip in seconds (auto-generated)';

COMMENT ON COLUMN parliament_member_clips.transcript IS 
'Full transcript of what the member said during this clip';

COMMENT ON COLUMN parliament_member_clips.transcript_embedding IS 
'Vector embedding of the transcript for semantic search (3072 dimensions for OpenAI text-embedding-3-large)';

COMMENT ON COLUMN parliament_member_clips.clip_url IS 
'Direct URL to the processed video clip file';

COMMENT ON COLUMN parliament_member_clips.full_video_path IS 
'Path to the full video file from which this clip was extracted';

COMMENT ON COLUMN parliament_member_clips.status IS 
'Processing status of the clip (processing, completed, failed, pending_review)';

COMMENT ON COLUMN parliament_member_clips.confidence_score IS 
'AI confidence score for transcript accuracy (0.000 to 1.000)';

COMMENT ON COLUMN parliament_member_clips.audio_quality_score IS 
'Audio quality assessment score (0.000 to 1.000)';

COMMENT ON COLUMN parliament_member_clips.is_deleted IS 
'Soft deletion flag. FALSE = active clip, TRUE = deleted';

COMMENT ON COLUMN parliament_member_clips.deleted_at IS 
'Timestamp when this clip was marked as deleted. NULL = never deleted';

-- Create function for semantic search of clips
CREATE OR REPLACE FUNCTION search_parliament_clips(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    max_results int DEFAULT 20,
    member_filter int DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    member_id int,
    transcript text,
    clip_url text,
    session_date date,
    debate_topic text,
    similarity float,
    start_timestamp timestamp with time zone,
    end_timestamp timestamp with time zone,
    duration_seconds decimal
)
LANGUAGE sql STABLE
AS $$
    SELECT
        pmc.id,
        pmc.member_id,
        pmc.transcript,
        pmc.clip_url,
        pmc.session_date,
        pmc.debate_topic,
        1 - (pmc.transcript_embedding <=> query_embedding) as similarity,
        pmc.start_timestamp,
        pmc.end_timestamp,
        pmc.duration_seconds
    FROM parliament_member_clips pmc
    WHERE 
        pmc.is_deleted = FALSE
        AND pmc.status = 'completed'
        AND pmc.transcript_embedding IS NOT NULL
        AND 1 - (pmc.transcript_embedding <=> query_embedding) > similarity_threshold
        AND (member_filter IS NULL OR pmc.member_id = member_filter)
    ORDER BY (pmc.transcript_embedding <=> query_embedding) ASC
    LIMIT max_results;
$$;

-- Grant execute permission on the search function
GRANT EXECUTE ON FUNCTION search_parliament_clips TO authenticated;
GRANT EXECUTE ON FUNCTION search_parliament_clips TO service_role;

-- Create function for full-text search of clips (complement to semantic search)
CREATE OR REPLACE FUNCTION search_parliament_clips_fulltext(
    search_query text,
    max_results int DEFAULT 20,
    member_filter int DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    member_id int,
    transcript text,
    clip_url text,
    session_date date,
    debate_topic text,
    rank float,
    start_timestamp timestamp with time zone,
    end_timestamp timestamp with time zone,
    duration_seconds decimal
)
LANGUAGE sql STABLE
AS $$
    SELECT
        pmc.id,
        pmc.member_id,
        pmc.transcript,
        pmc.clip_url,
        pmc.session_date,
        pmc.debate_topic,
        ts_rank(to_tsvector('english', pmc.transcript), plainto_tsquery('english', search_query)) as rank,
        pmc.start_timestamp,
        pmc.end_timestamp,
        pmc.duration_seconds
    FROM parliament_member_clips pmc
    WHERE 
        pmc.is_deleted = FALSE
        AND pmc.status = 'completed'
        AND to_tsvector('english', pmc.transcript) @@ plainto_tsquery('english', search_query)
        AND (member_filter IS NULL OR pmc.member_id = member_filter)
    ORDER BY ts_rank(to_tsvector('english', pmc.transcript), plainto_tsquery('english', search_query)) DESC
    LIMIT max_results;
$$;

-- Grant execute permission on the full-text search function
GRANT EXECUTE ON FUNCTION search_parliament_clips_fulltext TO authenticated;
GRANT EXECUTE ON FUNCTION search_parliament_clips_fulltext TO service_role; 