-- Fix type mismatches in search_clips_by_embedding function
-- session_date should be cast to text, and ensure proper type matching

DROP FUNCTION IF EXISTS search_clips_by_embedding(text, integer, integer, double precision);

CREATE OR REPLACE FUNCTION search_clips_by_embedding(
  search_query text,
  target_member_id integer,
  match_limit integer DEFAULT 50,
  similarity_threshold double precision DEFAULT 0.7
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
  similarity_score double precision
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
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
    pmc.session_date::text, -- Cast date to text
    pmc.session_type,
    pmc.debate_topic,
    pmc.status,
    pmc.created_at,
    -- Calculate text similarity as a placeholder for embedding similarity
    CASE 
      WHEN pmc.transcript IS NOT NULL AND pmc.transcript != '' THEN
        public.similarity(lower(pmc.transcript), lower(search_query))
      ELSE 0.0
    END::double precision as similarity_score
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
      -- Text similarity above threshold
      (
        pmc.transcript IS NOT NULL AND pmc.transcript != '' AND
        public.similarity(lower(pmc.transcript), lower(search_query)) >= similarity_threshold
      )
    )
  ORDER BY 
    -- Order by text similarity
    public.similarity(lower(pmc.transcript), lower(search_query)) DESC,
    pmc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_clips_by_embedding(text, integer, integer, double precision) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_clips_by_embedding(text, integer, integer, double precision) IS 
'Function to search parliament member clips using text similarity (placeholder for future embedding search). Used on create-clips page.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed type mismatches in search_clips_by_embedding function';
END;
$$;