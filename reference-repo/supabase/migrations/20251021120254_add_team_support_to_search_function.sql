-- Add team support to search_user_clips_by_embedding function
-- This allows searching clips by team_id in addition to user_id

-- Drop the old function
DROP FUNCTION IF EXISTS search_user_clips_by_embedding(text, uuid, integer, float);

-- Create new function with optional target_team_id parameter
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
  debate_topic text,
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
    pmc.debate_topic,
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
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
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

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float, uuid) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float, uuid) IS
'Function to search user clips or team clips by text similarity. Supports filtering by either user_id or team_id. Searches both user_clips.transcript and parliament_member_clips.transcript for comprehensive coverage.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Added team support to search_user_clips_by_embedding function';
    RAISE NOTICE 'Function now accepts optional target_team_id parameter for team clip searches';
END;
$$;
