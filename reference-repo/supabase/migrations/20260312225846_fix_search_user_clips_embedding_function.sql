-- Fix search_user_clips_by_embedding:
-- 1. Remove debate_topic (dropped from parliament_member_clips in 20251202124816)
-- 2. Drop both old overloads (4-param and 5-param) before recreating
-- 3. Preserve target_team_id parameter for team clip search
-- 4. Use vector(3072) + halfvec cosine distance for embedding similarity

-- Drop all existing overloads
DROP FUNCTION IF EXISTS search_user_clips_by_embedding(text, uuid, integer, float);
DROP FUNCTION IF EXISTS search_user_clips_by_embedding(text, uuid, integer, float, uuid);

CREATE OR REPLACE FUNCTION search_user_clips_by_embedding(
  query_embedding_text text,
  target_user_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.78,
  target_team_id uuid DEFAULT NULL
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
  similarity_score float,
  parliament_member_clips jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  query_embedding vector(3072);
BEGIN
  -- Ensure either target_user_id or target_team_id is provided
  IF target_user_id IS NULL AND target_team_id IS NULL THEN
    RAISE EXCEPTION 'Either target_user_id or target_team_id must be provided';
  END IF;

  query_embedding := query_embedding_text::vector(3072);

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
    uc.transcript,
    pmc.session_date,
    pmc.session_type,
    GREATEST(
      COALESCE(1 - (uc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.title_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
    )::float AS similarity_score,
    jsonb_build_object(
      'id', pmc.id,
      'member_id', pmc.member_id,
      'parliament_members', jsonb_build_object(
        'display_name', pm.display_name,
        'party_name', pm.party_name,
        'party_abbreviation', pm.party_abbreviation
      )
    ) AS parliament_member_clips
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.clip_id = pmc.id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.member_id
  WHERE
    -- Filter by team_id if provided, otherwise filter by user_id
    (
      (target_team_id IS NOT NULL AND uc.team_id = target_team_id)
      OR
      (target_team_id IS NULL AND uc.user_id = target_user_id)
    )
    AND uc.is_deleted = false
    AND pmc.is_deleted = false
    AND (uc.description_embedding IS NOT NULL OR uc.transcript_embedding IS NOT NULL OR uc.title_embedding IS NOT NULL)
    AND GREATEST(
      COALESCE(1 - (uc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.title_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- Grant permissions with correct 5-param signature
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float, uuid)
  TO service_role;
