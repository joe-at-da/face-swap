-- Make search_parliament_clips_by_vector null-safe and filter completed clips

-- Drop existing function with text signature if exists
DROP FUNCTION IF EXISTS search_parliament_clips_by_vector(text, integer, integer, float);

-- Recreate with text input; cast to vector(1536) internally
CREATE OR REPLACE FUNCTION search_parliament_clips_by_vector(
  query_embedding_text text,
  target_member_id integer,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.78
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
AS $$
DECLARE
  query_embedding vector(1536);
BEGIN
  -- Cast text to vector
  query_embedding := query_embedding_text::vector(1536);

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
    pmc.session_date::text,
    pmc.session_type::text,
    pmc.debate_topic,
    pmc.status,
    pmc.created_at,
    GREATEST(
      COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (pmc.transcript_embedding   <=> query_embedding), 0)
    ) AS similarity_score
  FROM parliament_member_clips pmc
  WHERE
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.status = 'completed'
    AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    AND GREATEST(
      COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (pmc.transcript_embedding   <=> query_embedding), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) TO service_role;

COMMENT ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) IS
'Semantic search on parliament_member_clips (completed only), null-safe over description/transcript embeddings, ordered by similarity.';


