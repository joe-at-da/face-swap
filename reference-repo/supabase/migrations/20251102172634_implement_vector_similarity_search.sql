-- Migration: Implement Vector Similarity Search for AI Similarity Feature
-- Purpose: Enable semantic search using description_embedding and transcript_embedding
--          for parliament_member_clips, and description_embedding and title_embedding
--          for user_clips. This allows finding clips by meaning/context rather than
--          exact keywords (e.g., "ambulances" will match "healthcare" queries).

-- ==============================================================================
-- 1. Parliament Member Clips Vector Similarity Search
-- ==============================================================================

CREATE OR REPLACE FUNCTION search_parliament_clips_by_vector(
  query_embedding vector(1536),
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
LANGUAGE sql
STABLE
AS $$
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
    pmc.debate_topic,
    pmc.status,
    pmc.created_at,
    -- Calculate similarity as the best match between description and transcript embeddings
    -- Using cosine distance operator <=> and converting to similarity (1 - distance)
    GREATEST(
      COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0.0),
      COALESCE(1 - (pmc.transcript_embedding <=> query_embedding), 0.0)
    )::float as similarity_score
  FROM parliament_member_clips pmc
  WHERE 
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.transcript IS NOT NULL
    AND pmc.transcript != ''
    AND (
      -- Check if description embedding matches above threshold
      (pmc.description_embedding IS NOT NULL AND 
       1 - (pmc.description_embedding <=> query_embedding) > match_threshold)
      OR
      -- Check if transcript embedding matches above threshold
      (pmc.transcript_embedding IS NOT NULL AND 
       1 - (pmc.transcript_embedding <=> query_embedding) > match_threshold)
    )
  ORDER BY 
    similarity_score DESC,
    pmc.created_at DESC
  LIMIT match_limit;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(vector, integer, integer, float) TO service_role;

-- Add comment
COMMENT ON FUNCTION search_parliament_clips_by_vector(vector, integer, integer, float) IS
'Performs semantic similarity search on parliament_member_clips using vector embeddings. Searches both description_embedding and transcript_embedding, returning clips ranked by similarity score. Uses cosine distance with a configurable threshold (default 0.78).';

-- ==============================================================================
-- 2. User Clips Vector Similarity Search
-- ==============================================================================

CREATE OR REPLACE FUNCTION search_user_clips_by_vector(
  query_embedding vector(1536),
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
  title text,
  description text,
  session_date date,
  session_type text,
  debate_topic text,
  similarity_score float,
  parliament_member_clips jsonb
)
LANGUAGE sql
STABLE
AS $$
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
    uc.title,
    uc.description,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    -- Calculate similarity as the best match between description and title embeddings
    -- Using cosine distance operator <=> and converting to similarity (1 - distance)
    GREATEST(
      COALESCE(1 - (uc.description_embedding <=> query_embedding), 0.0),
      COALESCE(1 - (uc.title_embedding <=> query_embedding), 0.0)
    )::float as similarity_score,
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
      (target_team_id IS NULL AND target_user_id IS NOT NULL AND uc.user_id = target_user_id)
    )
    AND uc.is_deleted = false
    AND pmc.is_deleted = false
    AND (
      -- Check if description embedding matches above threshold
      (uc.description_embedding IS NOT NULL AND 
       1 - (uc.description_embedding <=> query_embedding) > match_threshold)
      OR
      -- Check if title embedding matches above threshold
      (uc.title_embedding IS NOT NULL AND 
       1 - (uc.title_embedding <=> query_embedding) > match_threshold)
    )
  ORDER BY 
    similarity_score DESC,
    uc.created_at DESC
  LIMIT match_limit;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION search_user_clips_by_vector(vector, uuid, integer, float, uuid) TO service_role;

-- Add comment
COMMENT ON FUNCTION search_user_clips_by_vector(vector, uuid, integer, float, uuid) IS
'Performs semantic similarity search on user_clips using vector embeddings. Searches both description_embedding and title_embedding, returning clips ranked by similarity score. Supports filtering by user_id or team_id. Uses cosine distance with a configurable threshold (default 0.78).';

-- ==============================================================================
-- Log migration completion
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created vector similarity search functions';
    RAISE NOTICE 'Function: search_parliament_clips_by_vector - searches description_embedding and transcript_embedding';
    RAISE NOTICE 'Function: search_user_clips_by_vector - searches description_embedding and title_embedding';
    RAISE NOTICE 'Both functions use cosine distance (<=> operator) with default threshold of 0.78';
    RAISE NOTICE 'Results are ranked by similarity score (higher = more similar)';
END;
$$;

