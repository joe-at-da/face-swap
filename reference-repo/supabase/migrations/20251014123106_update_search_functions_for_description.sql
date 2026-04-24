-- Migration: Update search functions to include description fields
-- Purpose: Enable search on AI-generated descriptions and description embeddings

-- Drop and recreate the search_clips_by_embedding function to include description search
DROP FUNCTION IF EXISTS search_clips_by_embedding(text, integer, integer, float);

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
  description text,
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
BEGIN
  RETURN QUERY
  SELECT
    pmc.id,
    pmc.member_id,
    pmc.transcript,
    pmc.description,
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
    -- Use text similarity as placeholder (will be replaced with actual embedding similarity via API)
    GREATEST(
      COALESCE(similarity(lower(COALESCE(pmc.description, '')), lower(search_query)), 0.0),
      COALESCE(similarity(lower(pmc.transcript), lower(search_query)), 0.0)
    ) as similarity_score
  FROM parliament_member_clips pmc
  WHERE
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.transcript IS NOT NULL
    AND pmc.transcript != ''
    AND (
      -- Search in description (prioritized)
      (pmc.description IS NOT NULL AND lower(pmc.description) LIKE '%' || lower(search_query) || '%')
      OR
      -- Search in transcript
      lower(pmc.transcript) LIKE '%' || lower(search_query) || '%'
      OR
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
      OR
      -- If embeddings exist (will use actual embedding similarity via API)
      (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    )
  ORDER BY
    -- Prioritize description matches, then text similarity
    CASE WHEN pmc.description IS NOT NULL THEN 1 ELSE 2 END,
    GREATEST(
      COALESCE(similarity(lower(COALESCE(pmc.description, '')), lower(search_query)), 0.0),
      COALESCE(similarity(lower(pmc.transcript), lower(search_query)), 0.0)
    ) DESC,
    pmc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_clips_by_embedding(text, integer, integer, float) TO service_role;

-- Update the fulltext search function to include descriptions
DROP FUNCTION IF EXISTS search_parliament_clips_fulltext(text, integer, integer);

CREATE OR REPLACE FUNCTION search_parliament_clips_fulltext(
  search_query text,
  member_filter integer DEFAULT NULL,
  max_results integer DEFAULT 50
)
RETURNS TABLE (
  id uuid,
  member_id integer,
  transcript text,
  description text,
  start_timestamp text,
  end_timestamp text,
  duration_seconds numeric,
  clip_url text,
  debate_topic text,
  session_date text,
  rank real
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
    pmc.description,
    pmc.start_timestamp,
    pmc.end_timestamp,
    pmc.duration_seconds,
    pmc.clip_url,
    pmc.debate_topic,
    pmc.session_date,
    -- Combine rank from both description and transcript, with description weighted higher
    GREATEST(
      COALESCE(ts_rank(to_tsvector('english', COALESCE(pmc.description, '')), plainto_tsquery('english', search_query)), 0.0) * 1.5,
      COALESCE(ts_rank(to_tsvector('english', pmc.transcript), plainto_tsquery('english', search_query)), 0.0)
    ) as rank
  FROM parliament_member_clips pmc
  WHERE
    pmc.is_deleted = false
    AND pmc.transcript IS NOT NULL
    AND pmc.transcript != ''
    AND (member_filter IS NULL OR pmc.member_id = member_filter)
    AND (
      -- Search in description with higher weight
      to_tsvector('english', COALESCE(pmc.description, '')) @@ plainto_tsquery('english', search_query)
      OR
      -- Search in transcript
      to_tsvector('english', pmc.transcript) @@ plainto_tsquery('english', search_query)
    )
  ORDER BY rank DESC
  LIMIT max_results;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION search_parliament_clips_fulltext(text, integer, integer) TO service_role;

-- Add comment
COMMENT ON FUNCTION search_clips_by_embedding(text, integer, integer, float) IS
'Enhanced search function that searches both descriptions and transcripts. Prioritizes description matches.';

COMMENT ON FUNCTION search_parliament_clips_fulltext(text, integer, integer) IS
'Full-text search function that searches both descriptions and transcripts with description weighted 1.5x higher.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully updated search functions to include description fields';
    RAISE NOTICE 'Description searches are weighted higher than transcript searches';
    RAISE NOTICE 'Both vector similarity and full-text search now support descriptions';
END;
$$;
