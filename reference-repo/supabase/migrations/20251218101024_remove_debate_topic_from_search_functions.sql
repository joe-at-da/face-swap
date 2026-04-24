-- Migration: Remove debate_topic from search functions
-- The debate_topic column was dropped from parliament_member_clips in migration 20251202124816
-- This migration updates all search functions to remove references to debate_topic

-- =====================================================
-- DROP ALL EXISTING FUNCTIONS FIRST (required when changing return types)
-- =====================================================
DROP FUNCTION IF EXISTS search_parliament_clips(vector(1536), float, int, int);
DROP FUNCTION IF EXISTS search_parliament_clips_fulltext(text, int, int);
DROP FUNCTION IF EXISTS search_parliament_clips_by_vector(text, integer, integer, float);
DROP FUNCTION IF EXISTS search_user_clips_by_vector(text, uuid, integer, float, uuid);
DROP FUNCTION IF EXISTS search_parliament_clips_three_tier(text, integer, integer);

-- =====================================================
-- 1. Recreate search_parliament_clips function
-- =====================================================
CREATE OR REPLACE FUNCTION search_parliament_clips(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    max_results int DEFAULT 20,
    member_filter int DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    member_id int,
    transcript text,
    clip_url text,
    session_date date,
    similarity float,
    start_timestamp text,
    end_timestamp text,
    duration_seconds decimal
)
LANGUAGE sql STABLE
AS $$
    SELECT
        pmc.id,
        pmc.member_id,
        pmc.transcript,
        pmc.clip_url,
        pmc.session_date,
        1 - (pmc.transcript_embedding <=> query_embedding) as similarity,
        pmc.start_timestamp,
        pmc.end_timestamp,
        pmc.duration_seconds
    FROM parliament_member_clips pmc
    WHERE
        pmc.is_deleted = FALSE
        AND pmc.status = 'completed'
        AND pmc.transcript_embedding IS NOT NULL
        AND 1 - (pmc.transcript_embedding <=> query_embedding) > similarity_threshold
        AND (member_filter IS NULL OR pmc.member_id = member_filter)
    ORDER BY (pmc.transcript_embedding <=> query_embedding) ASC
    LIMIT max_results;
$$;

-- =====================================================
-- 2. Recreate search_parliament_clips_fulltext function
-- =====================================================
CREATE OR REPLACE FUNCTION search_parliament_clips_fulltext(
    search_query text,
    max_results int DEFAULT 20,
    member_filter int DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    member_id int,
    transcript text,
    clip_url text,
    session_date date,
    rank float,
    start_timestamp text,
    end_timestamp text,
    duration_seconds decimal
)
LANGUAGE sql STABLE
AS $$
    SELECT
        pmc.id,
        pmc.member_id,
        pmc.transcript,
        pmc.clip_url,
        pmc.session_date,
        ts_rank(to_tsvector('english', pmc.transcript), plainto_tsquery('english', search_query)) as rank,
        pmc.start_timestamp,
        pmc.end_timestamp,
        pmc.duration_seconds
    FROM parliament_member_clips pmc
    WHERE
        pmc.is_deleted = FALSE
        AND pmc.status = 'completed'
        AND to_tsvector('english', pmc.transcript) @@ plainto_tsquery('english', search_query)
        AND (member_filter IS NULL OR pmc.member_id = member_filter)
    ORDER BY ts_rank(to_tsvector('english', pmc.transcript), plainto_tsquery('english', search_query)) DESC
    LIMIT max_results;
$$;

-- =====================================================
-- 3. Recreate search_parliament_clips_by_vector function
-- =====================================================
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
  session_uid text,
  session_date text,
  session_type text,
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
    pmc.session_uid::text,
    pmc.session_date::text,
    pmc.session_type::text,
    pmc.status,
    pmc.created_at,
    GREATEST(
      COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (pmc.transcript_embedding   <=> query_embedding), 0)
    ) AS similarity_score
  FROM parliament_member_clips pmc
  WHERE
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.status = 'completed'
    AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    AND GREATEST(
      COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0),
      COALESCE(1 - (pmc.transcript_embedding   <=> query_embedding), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- =====================================================
-- 4. Recreate search_user_clips_by_vector function
-- =====================================================
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

-- =====================================================
-- 5. Recreate search_parliament_clips_three_tier function
-- =====================================================
CREATE OR REPLACE FUNCTION search_parliament_clips_three_tier(
  search_query text,
  target_member_id integer DEFAULT NULL,
  match_limit integer DEFAULT 50
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
  search_rank float,
  match_tier integer
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  search_lower text := lower(trim(search_query));
  search_terms text[];
BEGIN
  -- Prepare search terms for AND/OR logic
  search_terms := prepare_search_terms(search_query);

  RETURN QUERY
  WITH ranked_results AS (
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
      pmc.session_type,
      pmc.status,
      pmc.created_at,
      -- Determine match tier (1 = exact phrase, 2 = all words, 3 = any word)
      CASE
        -- Tier 1: Exact phrase match in any field
        WHEN lower(COALESCE(pmc.description, '')) LIKE '%' || search_lower || '%'
          OR lower(pmc.transcript) LIKE '%' || search_lower || '%'
        THEN 1
        -- Tier 2: All words present (AND logic)
        WHEN (
          -- Check if all terms are present in description
          COALESCE((SELECT bool_and(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if all terms are present in transcript
          COALESCE((SELECT bool_and(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 2
        -- Tier 3: Any word present (OR logic)
        WHEN (
          -- Check if any term is present in description
          COALESCE((SELECT bool_or(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if any term is present in transcript
          COALESCE((SELECT bool_or(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 3
        ELSE 4 -- No match (shouldn't happen due to WHERE clause)
      END AS match_tier,
      -- Calculate relevance score within each tier
      -- Prioritize: description > transcript
      (
        -- Score for description matches
        CASE
          WHEN lower(COALESCE(pmc.description, '')) LIKE '%' || search_lower || '%' THEN 1000.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 100.0
          ELSE 0.0
        END
        +
        -- Score for transcript matches (weighted 0.5x)
        CASE
          WHEN lower(pmc.transcript) LIKE '%' || search_lower || '%' THEN 500.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(pmc.transcript) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(pmc.transcript) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 50.0
          ELSE 0.0
        END
      ) AS search_rank
    FROM parliament_member_clips pmc
    WHERE
      pmc.is_deleted = false
      AND pmc.transcript IS NOT NULL
      AND pmc.transcript != ''
      AND (target_member_id IS NULL OR pmc.member_id = target_member_id)
      AND (
        -- At least one match condition must be true
        lower(COALESCE(pmc.description, '')) LIKE '%' || search_lower || '%'
        OR lower(pmc.transcript) LIKE '%' || search_lower || '%'
        OR COALESCE((SELECT bool_or(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        OR COALESCE((SELECT bool_or(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
      )
  )
  SELECT
    ranked_results.*
  FROM ranked_results
  WHERE ranked_results.match_tier <= 3
  ORDER BY
    ranked_results.match_tier ASC,          -- Tier 1 first, then 2, then 3
    ranked_results.search_rank DESC,         -- Within each tier, highest score first
    ranked_results.created_at DESC           -- Recent clips as tiebreaker
  LIMIT match_limit;
END;
$$;

-- =====================================================
-- Grant permissions
-- =====================================================
GRANT EXECUTE ON FUNCTION search_parliament_clips(vector(1536), float, int, int) TO authenticated;
GRANT EXECUTE ON FUNCTION search_parliament_clips(vector(1536), float, int, int) TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_fulltext(text, int, int) TO authenticated;
GRANT EXECUTE ON FUNCTION search_parliament_clips_fulltext(text, int, int) TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) TO service_role;
GRANT EXECUTE ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) TO authenticated;

-- =====================================================
-- Add comments
-- =====================================================
COMMENT ON FUNCTION search_parliament_clips(vector(1536), float, int, int) IS
'Performs semantic similarity search on parliament_member_clips using vector embeddings.';

COMMENT ON FUNCTION search_parliament_clips_fulltext(text, int, int) IS
'Performs full-text search on parliament_member_clips transcripts.';

COMMENT ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float) IS
'Semantic search on parliament_member_clips (completed only), null-safe over description/transcript embeddings, ordered by similarity. Returns session_uid for enriching with parliament_events data.';

COMMENT ON FUNCTION search_user_clips_by_vector(text, uuid, integer, float, uuid) IS
'Performs semantic similarity search on user_clips using vector embeddings. Accepts text parameter for easier JavaScript integration. Searches both description_embedding and title_embedding, returning clips ranked by similarity score.';

COMMENT ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) IS
'3-tier text search for parliament clips: 1) Exact phrase match, 2) All words present (AND), 3) Any word present (OR). Prioritizes description > transcript.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully removed debate_topic from all search functions';
    RAISE NOTICE 'Updated functions:';
    RAISE NOTICE '  - search_parliament_clips';
    RAISE NOTICE '  - search_parliament_clips_fulltext';
    RAISE NOTICE '  - search_parliament_clips_by_vector';
    RAISE NOTICE '  - search_user_clips_by_vector';
    RAISE NOTICE '  - search_parliament_clips_three_tier';
END $$;
