-- UK Parliament Member Face Encodings Table
-- Migration to store face encodings generated from MP portraits for face recognition and speaker identification
-- This table links face recognition data with parliament members and their portraits

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for storing face encodings
CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;

-- Create the parliament_member_face_encodings table
CREATE TABLE parliament_member_face_encodings (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to parliament_members
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
    
    -- Foreign key to the portrait that generated this encoding
    portrait_id UUID NOT NULL REFERENCES parliament_member_portraits(id) ON DELETE CASCADE,
    
    -- Face encoding as a vector (512-dimensional array from face_recognition library)
    face_encoding vector(512) NOT NULL,
    
    -- Alternative storage as JSON array (fallback if vector extension not available)
    face_encoding_json JSONB,
    
    -- Confidence score of the face detection (0.0 to 1.0)
    detection_confidence DECIMAL(5,4) DEFAULT NULL,
    
    -- Quality score of the face encoding (0.0 to 1.0)
    encoding_quality DECIMAL(5,4) DEFAULT NULL,
    
    -- Face bounding box coordinates from the portrait image
    face_bbox_top INTEGER,
    face_bbox_right INTEGER, 
    face_bbox_bottom INTEGER,
    face_bbox_left INTEGER,
    
    -- Portrait image dimensions when encoding was generated
    image_width INTEGER,
    image_height INTEGER,
    
    -- Processing metadata
    processing_model TEXT DEFAULT 'face_recognition_v1', -- Model used to generate encoding
    processing_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_version TEXT DEFAULT '1.0.0', -- Version of processing algorithm
    
    -- Flags
    is_primary_encoding BOOLEAN DEFAULT FALSE, -- True if from primary portrait
    is_validated BOOLEAN DEFAULT FALSE, -- True if manually validated
    is_active BOOLEAN DEFAULT TRUE, -- False if should be excluded from matching
    
    -- Soft deletion support
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Processing notes for debugging
    processing_notes TEXT DEFAULT NULL,
    error_message TEXT DEFAULT NULL
);

-- Create indexes for performance
CREATE INDEX idx_parliament_member_face_encodings_member_id ON parliament_member_face_encodings(member_id);
CREATE INDEX idx_parliament_member_face_encodings_portrait_id ON parliament_member_face_encodings(portrait_id);
CREATE INDEX idx_parliament_member_face_encodings_is_active ON parliament_member_face_encodings(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_parliament_member_face_encodings_is_primary ON parliament_member_face_encodings(is_primary_encoding) WHERE is_primary_encoding = TRUE;
CREATE INDEX idx_parliament_member_face_encodings_processing_date ON parliament_member_face_encodings(processing_date);
CREATE INDEX idx_parliament_member_face_encodings_is_deleted ON parliament_member_face_encodings(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_parliament_member_face_encodings_last_synced ON parliament_member_face_encodings(last_synced_at);

-- Create index for active, non-deleted encodings (most common query pattern)
CREATE INDEX idx_parliament_member_face_encodings_active 
ON parliament_member_face_encodings(member_id, is_deleted) 
WHERE is_active = TRUE AND is_deleted = FALSE;

-- Create composite index for common queries (member + primary + confidence)
CREATE INDEX idx_parliament_member_face_encodings_member_primary_confidence 
ON parliament_member_face_encodings(member_id, is_primary_encoding, detection_confidence) 
WHERE is_active = TRUE AND is_deleted = FALSE;

-- Create HNSW index for fast vector similarity search on face encodings
CREATE INDEX idx_parliament_member_face_encodings_vector_hnsw 
ON parliament_member_face_encodings 
USING hnsw (face_encoding vector_cosine_ops);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER update_parliament_member_face_encodings_updated_at 
    BEFORE UPDATE ON parliament_member_face_encodings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE parliament_member_face_encodings ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for authenticated users
CREATE POLICY "Parliament member face encodings are viewable by authenticated users" 
ON parliament_member_face_encodings
FOR SELECT 
USING (auth.role() = 'authenticated');

-- Add table and column comments for documentation
COMMENT ON TABLE parliament_member_face_encodings IS 
'Stores face encodings generated from MP portraits for facial recognition and speaker identification in videos';

COMMENT ON COLUMN parliament_member_face_encodings.member_id IS 
'Reference to parliament_members.member_id';

COMMENT ON COLUMN parliament_member_face_encodings.portrait_id IS 
'Reference to parliament_member_portraits.id that generated this encoding';

COMMENT ON COLUMN parliament_member_face_encodings.face_encoding IS 
'128-dimensional face encoding vector generated by face_recognition library';

COMMENT ON COLUMN parliament_member_face_encodings.face_encoding_json IS 
'Face encoding stored as JSON array (fallback for environments without vector support)';

COMMENT ON COLUMN parliament_member_face_encodings.detection_confidence IS 
'Confidence score of face detection (0.0-1.0, higher is better)';

COMMENT ON COLUMN parliament_member_face_encodings.encoding_quality IS 
'Quality assessment of the face encoding (0.0-1.0, higher is better)';

COMMENT ON COLUMN parliament_member_face_encodings.processing_model IS 
'Face recognition model used (face_recognition_v1, dlib_cnn, etc.)';

COMMENT ON COLUMN parliament_member_face_encodings.is_primary_encoding IS 
'True if generated from the MPs primary portrait';

COMMENT ON COLUMN parliament_member_face_encodings.is_validated IS 
'True if encoding has been manually validated for accuracy';

COMMENT ON COLUMN parliament_member_face_encodings.is_deleted IS 
'Soft deletion flag. FALSE = active encoding, TRUE = deleted';

COMMENT ON COLUMN parliament_member_face_encodings.deleted_at IS 
'Timestamp when this encoding was marked as deleted. NULL = never deleted';

-- Grant permissions for service role (for cron jobs and API operations)
GRANT ALL ON parliament_member_face_encodings TO service_role;

-- Grant permissions for authenticated users
GRANT SELECT ON parliament_member_face_encodings TO authenticated;