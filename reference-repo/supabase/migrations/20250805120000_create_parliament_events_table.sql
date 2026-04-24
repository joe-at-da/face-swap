-- Parliament Events Table Migration
-- Migration to store parliament events entries from Parliament Live TV feed
-- Simplified version with only essential fields from the API data

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum for processing status
CREATE TYPE parliament_event_processing_status AS ENUM (
    'pending',
    'processing', 
    'processed'
);

-- Parliament events table
CREATE TABLE parliament_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event identification (from API)
    event_id TEXT NOT NULL UNIQUE, -- The id field from the API
    
    -- Title information (flattened from title object)
    title_type TEXT, -- From title._type
    title TEXT NOT NULL, -- From title.__text
    
    -- Event timing
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, -- From updated field
    
    -- Author information (flattened from author object)
    author_name TEXT, -- From author.name
    
    -- Content information (flattened from content object)
    content_type TEXT, -- From content._type
    content_text TEXT, -- From content.__text
    
    -- Event URL
    event_url TEXT NOT NULL, -- From _xml:base
    
    -- Processing status
    status parliament_event_processing_status DEFAULT 'pending' NOT NULL,
    
    -- Soft deletion support
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at_local TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_event_url CHECK (event_url ~ '^https?://'),
    CONSTRAINT valid_event_id CHECK (length(event_id) > 0)
);

-- Create indexes for better query performance
CREATE INDEX idx_parliament_events_event_id ON parliament_events(event_id);
CREATE INDEX idx_parliament_events_updated_at ON parliament_events(updated_at);
CREATE INDEX idx_parliament_events_title ON parliament_events(title);
CREATE INDEX idx_parliament_events_status ON parliament_events(status);
CREATE INDEX idx_parliament_events_active ON parliament_events(event_id, is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_parliament_events_created_at ON parliament_events(created_at);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_parliament_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at_local = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_parliament_events_updated_at_trigger 
    BEFORE UPDATE ON parliament_events 
    FOR EACH ROW EXECUTE FUNCTION update_parliament_events_updated_at();

-- Enable Row Level Security (RLS)
ALTER TABLE parliament_events ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Parliament events are viewable by authenticated users" 
ON parliament_events
FOR SELECT 
USING (auth.role() = 'authenticated');

CREATE POLICY "Allow service role to manage parliament events" 
ON parliament_events
FOR ALL 
TO service_role
USING (true)
WITH CHECK (true);

-- Grant permissions
GRANT ALL ON parliament_events TO service_role;
GRANT SELECT ON parliament_events TO authenticated;

-- Add table and column comments for documentation
COMMENT ON TABLE parliament_events IS 
'Stores parliament events from Parliament Live TV feed';

COMMENT ON COLUMN parliament_events.event_id IS 
'Unique event identifier from Parliament Live TV API (from id field)';

COMMENT ON COLUMN parliament_events.title_type IS 
'Title type from title._type field';

COMMENT ON COLUMN parliament_events.title IS 
'Event title from title.__text field';

COMMENT ON COLUMN parliament_events.updated_at IS 
'Last updated timestamp from updated field';

COMMENT ON COLUMN parliament_events.author_name IS 
'Author name from author.name field';

COMMENT ON COLUMN parliament_events.content_type IS 
'Content type from content._type field';

COMMENT ON COLUMN parliament_events.content_text IS 
'Content text from content.__text field';

COMMENT ON COLUMN parliament_events.event_url IS 
'Event URL from _xml:base field';

COMMENT ON COLUMN parliament_events.status IS 
'Processing status: pending (default), processing, processed';

COMMENT ON COLUMN parliament_events.is_deleted IS 
'Soft deletion flag. FALSE = active event, TRUE = deleted';

COMMENT ON COLUMN parliament_events.deleted_at IS 
'Timestamp when this event was marked as deleted. NULL = never deleted';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Created parliament_events table:';
    RAISE NOTICE '- Stores events from Parliament Live TV feed';
    RAISE NOTICE '- Includes processing status tracking (pending, processing, processed)';
    RAISE NOTICE '- Supports soft deletion';
    RAISE NOTICE '- Maps directly to API JSON structure';
END $$;