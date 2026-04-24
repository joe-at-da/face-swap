-- Create function to search user clips by embedding similarity
-- This function searches through user clips by querying the associated parliament_member_clips
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
  watermark_position text,
  duration text,
  status parliament_clip_status,
  created_at timestamptz,
  updated_at timestamptz,
  transcript text,
  session_date text,
  session_type text,
  debate_topic text,
  similarity_score float,
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
    pmc.transcript,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    -- Calculate text similarity as a placeholder for embedding similarity
    CASE 
      WHEN pmc.transcript_embedding IS NOT NULL THEN 
        -- If we have embeddings, we would calculate cosine similarity here
        -- For now, use text similarity as approximation
        similarity(lower(pmc.transcript), lower(search_query))
      ELSE 0.0
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
    AND pmc.transcript IS NOT NULL
    AND pmc.transcript != ''
    AND (
      -- Full-text search in transcript
      lower(pmc.transcript) LIKE '%' || lower(search_query) || '%'
      OR 
      -- Search in debate topic
      (pmc.debate_topic IS NOT NULL AND lower(pmc.debate_topic) LIKE '%' || lower(search_query) || '%')
      OR
      -- If embeddings exist, we would add embedding similarity here
      (pmc.transcript_embedding IS NOT NULL)
    )
  ORDER BY 
    -- Order by text similarity for now, would use embedding similarity in production
    similarity(lower(pmc.transcript), lower(search_query)) DESC,
    uc.created_at DESC
  LIMIT match_limit;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) TO service_role;

-- Create indexes for better performance on user_clips queries
CREATE INDEX IF NOT EXISTS idx_user_clips_user_id_clip_id 
ON user_clips(user_id, clip_id) WHERE is_deleted = false;

-- Create index for user_clips status filtering
CREATE INDEX IF NOT EXISTS idx_user_clips_user_status 
ON user_clips(user_id, status) WHERE is_deleted = false;

-- Add comments
COMMENT ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float) IS 
'Function to search user clips using embedding similarity through joined parliament_member_clips. Currently uses text similarity as fallback until proper embedding search is implemented.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'User clips embedding search function created successfully';
    RAISE NOTICE 'Function searches through joined parliament_member_clips data';
    RAISE NOTICE 'Added composite indexes for better query performance';
    RAISE NOTICE 'Function supports text similarity as fallback for embedding search';
END;
$$;