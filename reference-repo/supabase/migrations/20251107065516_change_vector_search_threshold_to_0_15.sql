-- Change vector similarity search threshold from 0.2 to 0.15
-- This makes the search more permissive, returning more results with lower similarity scores

-- Update search_user_clips_by_vector function with new threshold
CREATE OR REPLACE FUNCTION search_user_clips_by_vector(
  query_embedding_text text,
  target_user_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.15,
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
  member_id integer,
  member_name text,
  member_party text,
  status parliament_clip_status,
  created_at timestamptz,
  segments jsonb,
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
    uc.clip_id as parliament_clip_id,
    uc.transcript,
    uc.title,
    uc.description,
    pmc.start_timestamp,
    pmc.end_timestamp,
    pmc.duration_seconds,
    uc.clip_url,
    uc.vertical_clip_url,
    uc.thumbnail_url,
    uc.vertical_thumbnail_url,
    pmc.session_date::text,
    pmc.session_type::text,
    pmc.debate_topic,
    pmc.member_id,
    pm.display_name as member_name,
    COALESCE(pm.party_name, pm.party_abbreviation) as member_party,
    uc.status,
    uc.created_at,
    uc.segments,
    GREATEST(
      COALESCE(1 - (uc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (uc.title_embedding <=> query_embedding), 0)
    ) as similarity_score
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.clip_id = pmc.id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.member_id
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
GRANT EXECUTE ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) TO service_role;

-- Update comment to reflect new threshold
COMMENT ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) IS
'Performs semantic similarity search on user_clips using vector embeddings. Accepts text parameter for easier JavaScript integration. Searches both description_embedding and title_embedding, returning clips ranked by similarity score. Uses cosine distance with a configurable threshold (default 0.15).';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated search_user_clips_by_vector threshold from 0.2 to 0.15';
    RAISE NOTICE 'This makes the search more permissive, returning more results with lower similarity scores';
END $$;

