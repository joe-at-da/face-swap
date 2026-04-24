-- Fix vector search functions to accept text parameter instead of vector
-- This makes it easier to call from JavaScript/PostgREST
-- The functions will cast the text to vector internally

-- Drop existing functions
DROP FUNCTION IF EXISTS search_parliament_clips_by_vector(vector, integer, integer, float);
DROP FUNCTION IF EXISTS search_user_clips_by_vector(vector, uuid, integer, float, uuid);

-- Recreate search_parliament_clips_by_vector with text parameter
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
      1 - (pmc.description_embedding <=> query_embedding),
      1 - (pmc.transcript_embedding <=> query_embedding)
    ) as similarity_score
  FROM parliament_member_clips pmc
  WHERE 
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.status = 'completed'
    AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    AND GREATEST(
      1 - (pmc.description_embedding <=> query_embedding),
      1 - (pmc.transcript_embedding <=> query_embedding)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- Recreate search_user_clips_by_vector with text parameter
CREATE OR REPLACE FUNCTION search_user_clips_by_vector(
  query_embedding_text text,
  target_user_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.78,
  target_team_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  team_id uuid,
  parliament_clip_id uuid,
  transcript text,
  title text,
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
  member_name text,
  member_party text,
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
    uc.id,
    uc.user_id,
    uc.team_id,
    uc.parliament_clip_id,
    uc.transcript,
    uc.title,
    uc.description,
    uc.start_timestamp,
    uc.end_timestamp,
    uc.duration_seconds,
    uc.clip_url,
    uc.vertical_clip_url,
    uc.thumbnail_url,
    uc.vertical_thumbnail_url,
    pmc.session_date::text,
    pmc.session_type::text,
    pmc.debate_topic,
    pm.display_name as member_name,
    pm.current_party as member_party,
    uc.status,
    uc.created_at,
    GREATEST(
      COALESCE(1 - (uc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (uc.title_embedding <=> query_embedding), 0)
    ) as similarity_score
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.parliament_clip_id = pmc.id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.id
  WHERE 
    uc.is_deleted = false
    AND uc.status = 'completed'
    AND (uc.description_embedding IS NOT NULL OR uc.title_embedding IS NOT NULL)
    AND (
      (target_user_id IS NOT NULL AND uc.user_id = target_user_id) OR
      (target_team_id IS NOT NULL AND uc.team_id = target_team_id)
    )
    AND GREATEST(
      COALESCE(1 - (uc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (uc.title_embedding <=> query_embedding), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) TO service_role;
GRANT EXECUTE ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) IS
'Performs semantic similarity search on parliament_member_clips using vector embeddings. Accepts text parameter for easier JavaScript integration. Searches both description_embedding and transcript_embedding, returning clips ranked by similarity score.';

COMMENT ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) IS
'Performs semantic similarity search on user_clips using vector embeddings. Accepts text parameter for easier JavaScript integration. Searches both description_embedding and title_embedding, returning clips ranked by similarity score.';

