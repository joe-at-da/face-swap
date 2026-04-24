-- Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create function to search clips by embedding similarity
CREATE OR REPLACE FUNCTION search_clips_by_embedding(
  search_query text,
  target_member_id integer,
  match_limit integer DEFAULT 50,
  similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE (
  id uuid,
  member_id integer,
  transcript text,
  start_timestamp text,
  end_timestamp text,
  duration_seconds numeric,
  clip_url text,
  vertical_clip_url text,
  thumbnail_url text,
  vertical_thumbnail_url text,
  session_date text,
  session_type text,
  debate_topic text,
  status parliament_clip_status,
  created_at timestamptz,
  similarity_score float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  search_embedding vector(1536);
BEGIN
  -- Generate embedding for the search query using OpenAI's text-embedding-3-small
  -- This would typically be done via an API call, but for now we'll use a placeholder
  -- In practice, this should call your embedding API endpoint
  -- For now, we'll perform a simple text search as fallback
  
  RETURN QUERY
  SELECT 
    pmc.id,
    pmc.member_id,
    pmc.transcript,
    pmc.start_timestamp,
    pmc.end_timestamp,
    pmc.duration_seconds,
    pmc.clip_url,
    pmc.vertical_clip_url,
    pmc.thumbnail_url,
    pmc.vertical_thumbnail_url,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    pmc.status,
    pmc.created_at,
    -- Calculate text similarity as a placeholder for embedding similarity
    CASE 
      WHEN pmc.transcript_embedding IS NOT NULL THEN 
        -- If we have embeddings, we would calculate cosine similarity here
        -- For now, use text similarity as approximation
        similarity(lower(pmc.transcript), lower(search_query))
      ELSE 0.0
    END as similarity_score
  FROM parliament_member_clips pmc
  WHERE 
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.transcript IS NOT NULL
    AND pmc.transcript != ''
    AND (
      -- Full-text search in transcript
      lower(pmc.transcript) LIKE '%' || lower(search_query) || '%'
      OR 
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
      OR
      -- If embeddings exist, we would add embedding similarity here
      (pmc.transcript_embedding IS NOT NULL)
    )
  ORDER BY 
    -- Order by text similarity for now, would use embedding similarity in production
    similarity(lower(pmc.transcript), lower(search_query)) DESC,
    pmc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_clips_by_embedding(text, integer, integer, float) TO service_role;

-- Create index for better text search performance
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_transcript_gin 
ON parliament_member_clips USING gin(to_tsvector('english', transcript));

-- Create index for member_id and status for faster filtering
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_member_status 
ON parliament_member_clips(member_id, status) WHERE is_deleted = false;

-- Add comments
COMMENT ON FUNCTION search_clips_by_embedding(text, integer, integer, float) IS 
'Function to search parliament member clips using embedding similarity. Currently uses text similarity as fallback until proper embedding search is implemented.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Clips embedding search function created successfully';
    RAISE NOTICE 'Added GIN index for full-text search on transcript';
    RAISE NOTICE 'Added composite index for member_id and status filtering';
    RAISE NOTICE 'Function supports text similarity as fallback for embedding search';
END;
$$;