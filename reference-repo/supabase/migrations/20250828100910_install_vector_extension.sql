-- Install pgvector extension for vector similarity search
-- This is required for embedding-based searches on the create-clips page

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant usage permissions to authenticated users and service role
GRANT USAGE ON SCHEMA public TO authenticated, service_role;

-- Verify the extension is installed properly
DO $$
BEGIN
    -- Test that vector type is available
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
        RAISE EXCEPTION 'Vector extension installation failed';
    END IF;
    
    RAISE NOTICE 'Vector extension installed successfully';
END;
$$;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Installed pgvector extension for embedding similarity search';
END;
$$;