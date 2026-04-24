-- Migration: Implement 3-tier text search for improved search results
-- Purpose: Search with priority: 1) Exact phrase match, 2) All words present (AND), 3) Any word present (OR)
-- This replaces the need for AI similarity search for basic text queries

-- Create helper function to prepare search query for AND/OR logic
CREATE OR REPLACE FUNCTION prepare_search_terms(search_text text)
RETURNS text[]
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  terms text[];
BEGIN
  -- Split search text by spaces and return as array
  SELECT array_agg(lower(trim(word)))
  INTO terms
  FROM unnest(string_to_array(search_text, ' ')) AS word
  WHERE trim(word) != '';

  RETURN terms;
END;
$$;

-- Create 3-tier search function for parliament_member_clips
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
  debate_topic text,
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
      pmc.debate_topic,
      pmc.status,
      pmc.created_at,
      -- Determine match tier (1 = exact phrase, 2 = all words, 3 = any word)
      CASE
        -- Tier 1: Exact phrase match in any field
        WHEN lower(COALESCE(pmc.description, '')) LIKE '%' || search_lower || '%'
          OR lower(pmc.transcript) LIKE '%' || search_lower || '%'
          OR lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || search_lower || '%'
        THEN 1
        -- Tier 2: All words present (AND logic)
        WHEN (
          -- Check if all terms are present in description
          COALESCE((SELECT bool_and(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if all terms are present in transcript
          COALESCE((SELECT bool_and(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if all terms are present in debate topic
          COALESCE((SELECT bool_and(lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 2
        -- Tier 3: Any word present (OR logic)
        WHEN (
          -- Check if any term is present in description
          COALESCE((SELECT bool_or(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if any term is present in transcript
          COALESCE((SELECT bool_or(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if any term is present in debate topic
          COALESCE((SELECT bool_or(lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 3
        ELSE 4 -- No match (shouldn't happen due to WHERE clause)
      END AS match_tier,
      -- Calculate relevance score within each tier
      -- Prioritize: description > debate_topic > transcript
      (
        -- Score for description matches
        CASE
          WHEN lower(COALESCE(pmc.description, '')) LIKE '%' || search_lower || '%' THEN 1000.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 100.0
          ELSE 0.0
        END
        +
        -- Score for debate_topic matches (weighted 0.8x)
        CASE
          WHEN lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || search_lower || '%' THEN 800.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 80.0
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
        OR lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || search_lower || '%'
        OR COALESCE((SELECT bool_or(lower(COALESCE(pmc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        OR COALESCE((SELECT bool_or(lower(pmc.transcript) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        OR COALESCE((SELECT bool_or(lower(COALESCE(pmc.debate_topic, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
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

-- Create 3-tier search function for user_clips
CREATE OR REPLACE FUNCTION search_user_clips_three_tier(
  search_query text,
  target_user_id uuid DEFAULT NULL,
  target_team_id uuid DEFAULT NULL,
  match_limit integer DEFAULT 50
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  title text,
  description text,
  transcript text,
  clip_url text,
  vertical_clip_url text,
  thumbnail_url text,
  vertical_thumbnail_url text,
  duration_seconds numeric,
  member_id integer,
  created_at timestamptz,
  updated_at timestamptz,
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
      uc.id,
      uc.user_id,
      uc.title,
      uc.description,
      uc.transcript,
      uc.clip_url,
      uc.vertical_clip_url,
      uc.thumbnail_url,
      uc.vertical_thumbnail_url,
      uc.duration_seconds,
      uc.member_id,
      uc.created_at,
      uc.updated_at,
      -- Determine match tier (1 = exact phrase, 2 = all words, 3 = any word)
      CASE
        -- Tier 1: Exact phrase match in any field
        WHEN lower(COALESCE(uc.title, '')) LIKE '%' || search_lower || '%'
          OR lower(COALESCE(uc.description, '')) LIKE '%' || search_lower || '%'
          OR lower(COALESCE(uc.transcript, '')) LIKE '%' || search_lower || '%'
        THEN 1
        -- Tier 2: All words present (AND logic)
        WHEN (
          -- Check if all terms are present in title
          COALESCE((SELECT bool_and(lower(COALESCE(uc.title, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if all terms are present in description
          COALESCE((SELECT bool_and(lower(COALESCE(uc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if all terms are present in transcript
          COALESCE((SELECT bool_and(lower(COALESCE(uc.transcript, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 2
        -- Tier 3: Any word present (OR logic)
        WHEN (
          -- Check if any term is present in title
          COALESCE((SELECT bool_or(lower(COALESCE(uc.title, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if any term is present in description
          COALESCE((SELECT bool_or(lower(COALESCE(uc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
          OR
          -- Check if any term is present in transcript
          COALESCE((SELECT bool_or(lower(COALESCE(uc.transcript, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        )
        THEN 3
        ELSE 4 -- No match (shouldn't happen due to WHERE clause)
      END AS match_tier,
      -- Calculate relevance score within each tier
      -- Prioritize: title > description > transcript
      (
        -- Score for title matches (highest priority)
        CASE
          WHEN lower(COALESCE(uc.title, '')) LIKE '%' || search_lower || '%' THEN 1200.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.title, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.title, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 120.0
          ELSE 0.0
        END
        +
        -- Score for description matches
        CASE
          WHEN lower(COALESCE(uc.description, '')) LIKE '%' || search_lower || '%' THEN 1000.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.description, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.description, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 100.0
          ELSE 0.0
        END
        +
        -- Score for transcript matches (weighted 0.5x)
        CASE
          WHEN lower(COALESCE(uc.transcript, '')) LIKE '%' || search_lower || '%' THEN 500.0
          WHEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.transcript, '')) LIKE '%' || term || '%') > 0
          THEN (SELECT count(*) FROM unnest(search_terms) AS term WHERE lower(COALESCE(uc.transcript, '')) LIKE '%' || term || '%')::float / array_length(search_terms, 1)::float * 50.0
          ELSE 0.0
        END
      ) AS search_rank
    FROM user_clips uc
    WHERE
      uc.is_deleted = false
      AND (target_user_id IS NULL OR uc.user_id = target_user_id)
      AND (target_team_id IS NULL OR uc.team_id = target_team_id)
      AND (
        -- At least one match condition must be true
        lower(COALESCE(uc.title, '')) LIKE '%' || search_lower || '%'
        OR lower(COALESCE(uc.description, '')) LIKE '%' || search_lower || '%'
        OR lower(COALESCE(uc.transcript, '')) LIKE '%' || search_lower || '%'
        OR COALESCE((SELECT bool_or(lower(COALESCE(uc.title, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        OR COALESCE((SELECT bool_or(lower(COALESCE(uc.description, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
        OR COALESCE((SELECT bool_or(lower(COALESCE(uc.transcript, '')) LIKE '%' || term || '%') FROM unnest(search_terms) AS term), false)
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION prepare_search_terms(text) TO service_role;
GRANT EXECUTE ON FUNCTION prepare_search_terms(text) TO authenticated;
GRANT EXECUTE ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION search_user_clips_three_tier(text, uuid, uuid, integer) TO service_role;
GRANT EXECUTE ON FUNCTION search_user_clips_three_tier(text, uuid, uuid, integer) TO authenticated;

-- Add comments
COMMENT ON FUNCTION prepare_search_terms(text) IS
'Helper function that splits search query into individual terms for AND/OR logic matching';

COMMENT ON FUNCTION search_parliament_clips_three_tier(text, integer, integer) IS
'3-tier text search for parliament clips: 1) Exact phrase match, 2) All words present (AND), 3) Any word present (OR). Prioritizes description > debate_topic > transcript.';

COMMENT ON FUNCTION search_user_clips_three_tier(text, uuid, uuid, integer) IS
'3-tier text search for user clips: 1) Exact phrase match, 2) All words present (AND), 3) Any word present (OR). Prioritizes title > description > transcript.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully created 3-tier text search functions';
    RAISE NOTICE 'Tier 1: Exact phrase match (highest priority)';
    RAISE NOTICE 'Tier 2: All words present (AND logic)';
    RAISE NOTICE 'Tier 3: Any word present (OR logic)';
    RAISE NOTICE 'Results are ordered by tier, then by relevance score, then by recency';
END;
$$;
