-- Create speaker_identifications table if it doesn't exist
CREATE TABLE IF NOT EXISTS speaker_identifications (
    id SERIAL PRIMARY KEY,
    capture_session_id INTEGER NOT NULL REFERENCES capture_sessions(id),
    status VARCHAR,
    results JSONB,
    output_file VARCHAR,
    threshold FLOAT DEFAULT 0.6,
    created_by_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_speaker_identifications_id ON speaker_identifications (id);
CREATE INDEX IF NOT EXISTS ix_speaker_identifications_status ON speaker_identifications (status);

-- Create parliament_transcriptions table if it doesn't exist
CREATE TABLE IF NOT EXISTS parliament_transcriptions (
    id SERIAL PRIMARY KEY,
    capture_session_id INTEGER NOT NULL REFERENCES capture_sessions(id),
    speaker_identification_id INTEGER REFERENCES speaker_identifications(id),
    language VARCHAR DEFAULT 'en',
    format VARCHAR DEFAULT 'txt',
    model VARCHAR DEFAULT 'medium',
    status VARCHAR,
    output_file VARCHAR,
    error_message TEXT,
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_parliament_transcriptions_id ON parliament_transcriptions (id);
CREATE INDEX IF NOT EXISTS ix_parliament_transcriptions_status ON parliament_transcriptions (status);

-- Create speakers table if it doesn't exist
CREATE TABLE IF NOT EXISTS speakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    parliament_id VARCHAR,
    party VARCHAR,
    constituency VARCHAR,
    photo_url VARCHAR,
    face_encoding JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_speakers_id ON speakers (id);
CREATE INDEX IF NOT EXISTS ix_speakers_name ON speakers (name);
CREATE INDEX IF NOT EXISTS ix_speakers_parliament_id ON speakers (parliament_id);

-- Create speaker_appearances table if it doesn't exist
CREATE TABLE IF NOT EXISTS speaker_appearances (
    id SERIAL PRIMARY KEY,
    speaker_id INTEGER NOT NULL REFERENCES speakers(id),
    identification_id INTEGER NOT NULL REFERENCES speaker_identifications(id),
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_speaker_appearances_id ON speaker_appearances (id);

-- Add missing columns to capture_sessions if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='title') THEN
        ALTER TABLE capture_sessions ADD COLUMN title VARCHAR;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='description') THEN
        ALTER TABLE capture_sessions ADD COLUMN description VARCHAR;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='source_url') THEN
        ALTER TABLE capture_sessions ADD COLUMN source_url VARCHAR;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='file_path') THEN
        ALTER TABLE capture_sessions ADD COLUMN file_path VARCHAR;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='file_size') THEN
        ALTER TABLE capture_sessions ADD COLUMN file_size INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='duration') THEN
        ALTER TABLE capture_sessions ADD COLUMN duration FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='start_time') THEN
        ALTER TABLE capture_sessions ADD COLUMN start_time TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='end_time') THEN
        ALTER TABLE capture_sessions ADD COLUMN end_time TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='scheduled_start') THEN
        ALTER TABLE capture_sessions ADD COLUMN scheduled_start TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='scheduled_end') THEN
        ALTER TABLE capture_sessions ADD COLUMN scheduled_end TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='capture_sessions' AND column_name='metadata') THEN
        ALTER TABLE capture_sessions ADD COLUMN metadata JSONB;
    END IF;
END $$;
