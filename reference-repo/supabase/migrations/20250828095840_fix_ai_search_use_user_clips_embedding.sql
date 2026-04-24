-- Fix AI similarity search to use user_clips.transcript_embedding for my-clips page
-- This follows the architecture: parliament_member_clips for create-clips, user_clips for my-clips

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
    -- Return user_clips transcript (the full version) for display
    COALESCE(uc.transcript, pmc.transcript) as transcript,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    -- Calculate similarity using user_clips transcript and embedding when available
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
    uc.user_id = target_user_id
    AND uc.is_deleted = false
    AND pmc.is_deleted = false
    AND (
      -- Search in user_clips transcript (full version) first
      (uc.transcript IS NOT NULL AND uc.transcript != '' AND 
       lower(uc.transcript) LIKE '%' || lower(search_query) || '%')
      OR 
      -- Fallback to parliament_member_clips transcript 
      (pmc.transcript IS NOT NULL AND pmc.transcript != '' AND
       lower(pmc.transcript) LIKE '%' || lower(search_query) || '%')
      OR 
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
      OR
      -- Text similarity above threshold - prioritize user_clips transcript
      (
        (uc.transcript IS NOT NULL AND uc.transcript != '' AND
         public.similarity(lower(uc.transcript), lower(search_query)) >= similarity_threshold)
        OR
        (pmc.transcript IS NOT NULL AND pmc.transcript != '' AND
         public.similarity(lower(pmc.transcript), lower(search_query)) >= similarity_threshold)
      )
      -- TODO: Add vector similarity search using user_clips.transcript_embedding when implementing full embedding search
      -- OR (uc.transcript_embedding IS NOT NULL AND <embedding_similarity_condition>)
    )
  ORDER BY 
    -- Order by similarity score - prioritize user_clips transcript
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
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) TO service_role;

-- Add comments
COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) IS 
'Function to search user clips prioritizing user_clips.transcript and user_clips.transcript_embedding for my-clips page. Uses parliament_member_clips data as fallback and for metadata.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated search function to prioritize user_clips data for my-clips page searches';
END;
$$;