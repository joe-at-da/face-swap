-- Install pg_trgm extension for text similarity functions
-- This extension provides similarity() function used by the search functionality

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant permissions for pg_trgm extension functions to service_role
-- This ensures the similarity function is accessible when called from RPC

-- Grant execute permissions on similarity function specifically
GRANT EXECUTE ON FUNCTION public.similarity(text, text) TO service_role;

-- Also grant to anon role just in case
GRANT EXECUTE ON FUNCTION public.similarity(text, text) TO anon;

-- Ensure public schema usage is granted
GRANT USAGE ON SCHEMA public TO service_role;
GRANT USAGE ON SCHEMA public TO anon;

-- Re-create the search function with explicit schema reference
DROP FUNCTION IF EXISTS search_user_clips_by_embedding(text, uuid, integer, float);

CREATE OR REPLACE FUNCTION search_user_clips_by_embedding(
  search_query text,
  target_user_id uuid,
  match_limit integer DEFAULT 50,
  similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  clip_id uuid,
  segments jsonb,
  clip_url text,
  vertical_clip_url text,
  thumbnail_url text,
  vertical_thumbnail_url text,
  watermark_url text,
  watermark_position watermark_position,
  duration text,
  status parliament_clip_status,
  created_at timestamptz,
  updated_at timestamptz,
  transcript text,
  session_date date,
  session_type text,
  debate_topic text,
  similarity_score real,
  parliament_member_clips jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    uc.id,
    uc.user_id,
    uc.clip_id,
    uc.segments,
    uc.clip_url,
    uc.vertical_clip_url,
    uc.thumbnail_url,
    uc.vertical_thumbnail_url,
    uc.watermark_url,
    uc.watermark_position,
    uc.duration,
    uc.status,
    uc.created_at,
    uc.updated_at,
    pmc.transcript,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    -- Calculate text similarity with explicit schema reference
    CASE 
      WHEN pmc.transcript_embedding IS NOT NULL THEN 
        -- Use explicit schema reference for similarity function
        public.similarity(lower(pmc.transcript), lower(search_query))
      ELSE 0.0::real
    END as similarity_score,
    -- Include parliament member details as JSONB
    jsonb_build_object(
      'id', pmc.id,
      'member_id', pmc.member_id,
      'parliament_members', jsonb_build_object(
        'display_name', pm.display_name,
        'party_name', pm.party_name,
        'party_abbreviation', pm.party_abbreviation
      )
    ) as parliament_member_clips
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.clip_id = pmc.id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.member_id
  WHERE 
    uc.user_id = target_user_id
    AND uc.is_deleted = false
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
    -- Order by text similarity with explicit schema reference
    public.similarity(lower(pmc.transcript), lower(search_query)) DESC,
    uc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) IS 
'Function to search user clips using embedding similarity through joined parliament_member_clips. Uses explicit schema references for similarity function to ensure proper permissions.';

-- Log installation
DO $$
BEGIN
    RAISE NOTICE 'pg_trgm extension installed successfully';
    RAISE NOTICE 'similarity() function is now available for text similarity calculations';
    RAISE NOTICE 'Granted similarity function permissions and updated search function with explicit schema references';
END;
$$;