-- Migration: Remove debate_topic from remaining search functions
-- Fixes search_clips_by_embedding and search_user_clips_by_embedding

-- =====================================================
-- DROP EXISTING FUNCTIONS
-- =====================================================
DROP FUNCTION IF EXISTS search_clips_by_embedding(text, integer, integer, float);
DROP FUNCTION IF EXISTS search_user_clips_by_embedding(text, uuid, integer, float, uuid);

-- =====================================================
-- 1. Recreate search_clips_by_embedding function
-- =====================================================
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

-- =====================================================
-- 2. Recreate search_user_clips_by_embedding function
-- =====================================================
CREATE OR REPLACE FUNCTION search_user_clips_by_embedding(
  search_query text,
  target_user_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50,
  similarity_threshold float DEFAULT 0.7,
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
  similarity_score real,
  parliament_member_clips jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Ensure either target_user_id or target_team_id is provided
  IF target_user_id IS NULL AND target_team_id IS NULL THEN
    RAISE EXCEPTION 'Either target_user_id or target_team_id must be provided';
  END IF;

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
    pmc.transcript, -- Return parliament_member_clips transcript
    pmc.session_date,
    pmc.session_type,
    -- Calculate text similarity - search both transcripts but use user_clips for similarity when available
    CASE
      WHEN uc.transcript IS NOT NULL AND uc.transcript != '' THEN
        public.similarity(lower(uc.transcript), lower(search_query))
      WHEN pmc.transcript IS NOT NULL AND pmc.transcript != '' THEN
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
    -- Filter by team_id if provided, otherwise filter by user_id
    (
      (target_team_id IS NOT NULL AND uc.team_id = target_team_id)
      OR
      (target_team_id IS NULL AND uc.user_id = target_user_id)
    )
    AND uc.is_deleted = false
    AND pmc.is_deleted = false
    AND (
      -- Full-text search in both transcript fields
      (uc.transcript IS NOT NULL AND lower(uc.transcript) LIKE '%' || lower(search_query) || '%')
      OR
      (pmc.transcript IS NOT NULL AND lower(pmc.transcript) LIKE '%' || lower(search_query) || '%')
      OR
      -- Text similarity above threshold using the appropriate transcript
      (
        (uc.transcript IS NOT NULL AND uc.transcript != '' AND
         public.similarity(lower(uc.transcript), lower(search_query)) >= similarity_threshold)
        OR
        (pmc.transcript IS NOT NULL AND pmc.transcript != '' AND
         public.similarity(lower(pmc.transcript), lower(search_query)) >= similarity_threshold)
      )
    )
  ORDER BY
    -- Order by text similarity using the best available transcript
    CASE
      WHEN uc.transcript IS NOT NULL AND uc.transcript != '' THEN
        public.similarity(lower(uc.transcript), lower(search_query))
      WHEN pmc.transcript IS NOT NULL AND pmc.transcript != '' THEN
        public.similarity(lower(pmc.transcript), lower(search_query))
      ELSE 0.0::real
    END DESC,
    uc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- =====================================================
-- Grant permissions
-- =====================================================
GRANT EXECUTE ON FUNCTION search_clips_by_embedding(text, integer, integer, float) TO service_role;
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float, uuid) TO service_role;

-- =====================================================
-- Add comments
-- =====================================================
COMMENT ON FUNCTION search_clips_by_embedding(text, integer, integer, float) IS
'Enhanced search function that searches both descriptions and transcripts. Prioritizes description matches.';

COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float, uuid) IS
'Function to search user clips or team clips by text similarity. Supports filtering by either user_id or team_id. Searches both user_clips.transcript and parliament_member_clips.transcript for comprehensive coverage.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully removed debate_topic from remaining search functions';
    RAISE NOTICE 'Updated functions:';
    RAISE NOTICE '  - search_clips_by_embedding';
    RAISE NOTICE '  - search_user_clips_by_embedding';
END $$;
