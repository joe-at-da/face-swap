"""
Upgrade to 512D face encodings with pgvector support.

This migration implements the hybrid approach by:
1. Adding pgvector extension for 512D vector storage
2. Creating new face_encodings table with HNSW indexing
3. Migrating existing data to new format
4. Adding comprehensive metadata support
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers
revision = 'upgrade_to_512d_face_encodings'
down_revision = 'add_recognition_progress'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade to 512D face encodings with pgvector support."""
    
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create parliament_members table if it doesn't exist (for compatibility)
    op.execute("""
        CREATE TABLE IF NOT EXISTS parliament_members (
            member_id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            party VARCHAR(255),
            constituency VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create parliament_member_portraits table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS parliament_member_portraits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            member_id INTEGER REFERENCES parliament_members(member_id) ON DELETE CASCADE,
            portrait_url VARCHAR(500),
            portrait_path VARCHAR(500),
            is_primary BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create the new face encodings table with MPAI's superior schema
    op.execute("""
        CREATE TABLE parliament_member_face_encodings (
            -- Primary key
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            
            -- Foreign key to parliament_members
            member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
            
            -- Foreign key to the portrait that generated this encoding
            portrait_id UUID REFERENCES parliament_member_portraits(id) ON DELETE CASCADE,
            
            -- Face encoding as a vector (512-dimensional array)
            face_encoding vector(512) NOT NULL,
            
            -- Alternative storage as JSON array (fallback)
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
            processing_model TEXT DEFAULT 'face_recognition_v2',
            processing_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            processing_version TEXT DEFAULT '2.0.0',
            
            -- Flags
            is_primary_encoding BOOLEAN DEFAULT FALSE,
            is_validated BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            
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
        )
    """)
    
    # Create indexes for performance
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_member_id 
        ON parliament_member_face_encodings(member_id)
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_portrait_id 
        ON parliament_member_face_encodings(portrait_id)
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_is_active 
        ON parliament_member_face_encodings(is_active) WHERE is_active = TRUE
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_is_primary 
        ON parliament_member_face_encodings(is_primary_encoding) WHERE is_primary_encoding = TRUE
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_processing_date 
        ON parliament_member_face_encodings(processing_date)
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_is_deleted 
        ON parliament_member_face_encodings(is_deleted) WHERE is_deleted = FALSE
    """)
    
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_last_synced 
        ON parliament_member_face_encodings(last_synced_at)
    """)
    
    # Create composite index for common queries
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_member_primary_confidence 
        ON parliament_member_face_encodings(member_id, is_primary_encoding, detection_confidence) 
        WHERE is_active = TRUE AND is_deleted = FALSE
    """)
    
    # Create HNSW index for fast vector similarity search
    op.execute("""
        CREATE INDEX idx_parliament_member_face_encodings_vector_hnsw 
        ON parliament_member_face_encodings 
        USING hnsw (face_encoding vector_cosine_ops)
    """)
    
    # Create trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            NEW.last_synced_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_parliament_member_face_encodings_updated_at 
            BEFORE UPDATE ON parliament_member_face_encodings 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Migrate existing face_profiles data
    op.execute("""
        INSERT INTO parliament_members (member_id, name, party)
        SELECT 
            id, 
            name, 
            party
        FROM face_profiles 
        WHERE id IS NOT NULL
        ON CONFLICT (member_id) DO UPDATE SET
            name = EXCLUDED.name,
            party = EXCLUDED.party,
            updated_at = NOW()
    """)
    
    # Create portraits for existing face profiles
    op.execute("""
        INSERT INTO parliament_member_portraits (member_id, portrait_url, portrait_path, is_primary)
        SELECT 
            fp.id,
            fp.face_image_path,
            fp.face_image_path,
            TRUE
        FROM face_profiles fp 
        WHERE fp.face_image_path IS NOT NULL
    """)
    
    # Migrate face encodings (convert JSON to 512D vectors)
    op.execute("""
        INSERT INTO parliament_member_face_encodings (
            member_id, 
            portrait_id, 
            face_encoding, 
            face_encoding_json,
            detection_confidence,
            encoding_quality,
            processing_model,
            processing_version,
            is_primary_encoding,
            is_validated,
            is_active
        )
        SELECT 
            fp.id as member_id,
            pmp.id as portrait_id,
            -- Convert 128D JSON to 512D by padding with zeros
            CASE 
                WHEN fp.face_encoding IS NOT NULL THEN
                    array_cat(
                        string_to_array(fp.face_encoding::text, ',')::real[],
                        array_fill(0.0, ARRAY[384])
                    )::vector
                ELSE array_fill(0.0, ARRAY[512])::vector
            END as face_encoding,
            fp.face_encoding as face_encoding_json,
            COALESCE(fp.confidence_score, 0.8) as detection_confidence,
            CASE 
                WHEN fp.confidence_score > 0.8 THEN 0.9
                WHEN fp.confidence_score > 0.6 THEN 0.7
                ELSE 0.5
            END as encoding_quality,
            'face_recognition_v2' as processing_model,
            '2.0.0' as processing_version,
            TRUE as is_primary_encoding,
            fp.is_verified as is_validated,
            TRUE as is_active
        FROM face_profiles fp
        LEFT JOIN parliament_member_portraits pmp ON pmp.member_id = fp.id AND pmp.is_primary = TRUE
        WHERE fp.face_encoding IS NOT NULL
    """)


def downgrade():
    """Downgrade from 512D face encodings."""
    
    # Drop the new tables in reverse order
    op.execute('DROP TABLE IF EXISTS parliament_member_face_encodings')
    op.execute('DROP TABLE IF EXISTS parliament_member_portraits')
    op.execute('DROP TABLE IF EXISTS parliament_members')
    
    # Drop the pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector')
    
    # Drop the trigger function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
