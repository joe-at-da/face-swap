-- Fix search_user_clips_by_vector function column references
-- The function was using incorrect column names:
-- 1. uc.parliament_clip_id should be uc.clip_id
-- 2. Fields like start_timestamp, end_timestamp, duration_seconds should come from pmc, not uc
-- 3. Join should use pm.member_id not pm.id
-- 4. Party field should use pm.party_name or pm.party_abbreviation, not pm.current_party

-- Drop existing function
DROP FUNCTION IF EXISTS search_user_clips_by_vector(text, uuid, integer, float, uuid);

-- Recreate with correct column references
CREATE OR REPLACE FUNCTION search_user_clips_by_vector(
  query_embedding_text text,
  target_user_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.2,
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
    uc.clip_id as parliament_clip_id,  -- Fixed: use clip_id, alias as parliament_clip_id for API compatibility
    uc.transcript,
    uc.title,
    uc.description,
    pmc.start_timestamp,  -- Fixed: get from pmc, not uc
    pmc.end_timestamp,    -- Fixed: get from pmc, not uc
    pmc.duration_seconds, -- Fixed: get from pmc, not uc
    uc.clip_url,
    uc.vertical_clip_url,
    uc.thumbnail_url,
    uc.vertical_thumbnail_url,
    pmc.session_date::text,
    pmc.session_type::text,
    pmc.debate_topic,
    pmc.member_id,  -- Include member_id for proper nesting
    pm.display_name as member_name,
    COALESCE(pm.party_name, pm.party_abbreviation) as member_party,  -- Fixed: use party_name or party_abbreviation, not current_party
    uc.status,
    uc.created_at,
    uc.segments,  -- Include segments for display
    GREATEST(
      COALESCE(1 - (uc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (uc.title_embedding <=> query_embedding), 0)
    ) as similarity_score
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.clip_id = pmc.id  -- Fixed: use clip_id, not parliament_clip_id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.member_id  -- Fixed: use pm.member_id, not pm.id
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

-- Add comment
COMMENT ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) IS
'Performs semantic similarity search on user_clips using vector embeddings. Accepts text parameter for easier JavaScript integration. Searches both description_embedding and title_embedding, returning clips ranked by similarity score. Fixed column references: uses clip_id, gets timestamp fields from parliament_member_clips, uses correct parliament_members join.';

