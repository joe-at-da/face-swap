-- Fix search function to use user_clips.transcript instead of parliament_member_clips.transcript
-- The user_clips.transcript contains the full content while parliament_member_clips.transcript is shorter

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
    uc.transcript,  -- Return the full user_clips transcript
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    -- Calculate text similarity using user_clips.transcript (the full version)
    CASE 
      WHEN uc.transcript IS NOT NULL AND uc.transcript != '' THEN
        public.similarity(lower(uc.transcript), lower(search_query))
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
    AND uc.transcript IS NOT NULL  -- Check user_clips transcript
    AND uc.transcript != ''
    AND (
      -- Full-text search in user_clips transcript (the full version)
      lower(uc.transcript) LIKE '%' || lower(search_query) || '%'
      OR 
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
      OR
      -- Text similarity above threshold using user_clips transcript
      (
        uc.transcript IS NOT NULL AND uc.transcript != '' AND
        public.similarity(lower(uc.transcript), lower(search_query)) >= similarity_threshold
      )
    )
  ORDER BY 
    -- Order by text similarity using user_clips transcript
    CASE 
      WHEN uc.transcript IS NOT NULL AND uc.transcript != '' THEN
        public.similarity(lower(uc.transcript), lower(search_query))
      ELSE 0.0::real
    END DESC,
    uc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) IS 
'Function to search user clips using the full transcript content from user_clips.transcript instead of the shorter parliament_member_clips.transcript.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed search function to use full user_clips.transcript content';
END;
$$;