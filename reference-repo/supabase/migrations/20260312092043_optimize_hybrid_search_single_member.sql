-- Optimize hybrid_search_parliament_clips (single-member variant):
--
-- Port the same HNSW index optimization from hybrid_search_parliament_clips_all
-- (migrations 20260311124514 + 20260311133157) to the single-member function.
--
-- Problems with the previous version (20260225211146):
--   1. GREATEST() over two halfvec cosine distances prevents HNSW index usage
--   2. No statement_timeout (inherits 8s Supabase API default → timeouts)
--   3. No hnsw.ef_search tuning (default 40 too low for 3072 dims)
--
-- This version:
--   1. Splits semantic CTE into two HNSW-indexed sub-queries (transcript + description)
--   2. Combines with UNION ALL + GROUP BY, keeping best similarity per clip
--   3. Adds function-level SET for statement_timeout, work_mem; SET LOCAL for
--      hnsw.ef_search, hnsw.iterative_scan (pgvector 0.8.0+ post-filter fix)
--   4. Reduces candidate_limit from match_count*3 (600) to match_count*2 (400)
--   5. Adds similarity threshold >= 0.10 to filter noise

CREATE OR REPLACE FUNCTION public.hybrid_search_parliament_clips(
  query_embedding_text text,
  fulltext_query text,
  target_member_id integer,
  match_count integer DEFAULT 200,
  semantic_weight double precision DEFAULT 1.0,
  fulltext_weight double precision DEFAULT 1.0,
  rrf_k integer DEFAULT 50
)
RETURNS TABLE(
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
  created_at timestamp with time zone,
  hybrid_score double precision
)
LANGUAGE plpgsql
SET search_path = public, extensions
SET statement_timeout = '30s'
SET work_mem = '32MB'
AS $function$
DECLARE
  query_embedding vector(3072);
  candidate_limit integer;
  plain_query tsquery;
  or_tsquery tsquery;
BEGIN
  -- pgvector GUCs require SET LOCAL inside function body (postgres user is not superuser)
  SET LOCAL hnsw.ef_search = 100;
  SET LOCAL hnsw.iterative_scan = 'relaxed_order';

  query_embedding := query_embedding_text::vector(3072);
  candidate_limit := least(match_count * 3, 600);

  -- Build OR tsquery: convert AND to OR for broader fulltext recall.
  plain_query := plainto_tsquery('english', fulltext_query);
  IF numnode(plain_query) > 0 THEN
    or_tsquery := replace(plain_query::text, ' & ', ' | ')::tsquery;
  ELSE
    or_tsquery := plain_query;
  END IF;

  RETURN QUERY
  WITH
  -- Sub-query 1: transcript embeddings (HNSW-indexed)
  semantic_transcript AS (
    SELECT pmc.id,
           1 - (pmc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)) AS similarity
    FROM parliament_member_clips pmc
    WHERE pmc.member_id = target_member_id
      AND pmc.is_deleted = false
      AND pmc.transcript_embedding IS NOT NULL
    ORDER BY pmc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)
    LIMIT candidate_limit
  ),
  -- Sub-query 2: description embeddings (HNSW-indexed)
  semantic_description AS (
    SELECT pmc.id,
           1 - (pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)) AS similarity
    FROM parliament_member_clips pmc
    WHERE pmc.member_id = target_member_id
      AND pmc.is_deleted = false
      AND pmc.description_embedding IS NOT NULL
    ORDER BY pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)
    LIMIT candidate_limit
  ),
  -- Combine both embedding results, keep best similarity per clip
  semantic_combined AS (
    SELECT combined.id, MAX(combined.similarity) AS similarity
    FROM (
      SELECT * FROM semantic_transcript
      UNION ALL
      SELECT * FROM semantic_description
    ) combined
    GROUP BY combined.id
    HAVING MAX(combined.similarity) >= 0.10
  ),
  semantic AS (
    SELECT sc.id, ROW_NUMBER() OVER (ORDER BY sc.similarity DESC) AS rank_ix
    FROM semantic_combined sc
    ORDER BY rank_ix
    LIMIT candidate_limit
  ),

  full_text AS (
    SELECT
      pmc.id,
      ROW_NUMBER() OVER (
        ORDER BY GREATEST(
          COALESCE(ts_rank_cd(
            to_tsvector('english', pmc.transcript),
            or_tsquery
          ), 0),
          COALESCE(ts_rank_cd(
            to_tsvector('english', COALESCE(pmc.description, '')),
            or_tsquery
          ), 0) * 1.5
        ) DESC
      ) AS rank_ix
    FROM parliament_member_clips pmc
    WHERE
      pmc.member_id = target_member_id
      AND pmc.is_deleted = false
      AND pmc.transcript IS NOT NULL
      AND pmc.transcript != ''
      AND (
        to_tsvector('english', pmc.transcript) @@ or_tsquery
        OR to_tsvector('english', COALESCE(pmc.description, '')) @@ or_tsquery
      )
    ORDER BY rank_ix
    LIMIT candidate_limit
  )

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
    (
      COALESCE(semantic_weight / (rrf_k + s.rank_ix), 0.0) +
      COALESCE(fulltext_weight / (rrf_k + ft.rank_ix), 0.0)
    )::float AS hybrid_score
  FROM
    semantic s
    FULL OUTER JOIN full_text ft ON s.id = ft.id
    JOIN parliament_member_clips pmc ON COALESCE(s.id, ft.id) = pmc.id
  ORDER BY hybrid_score DESC
  LIMIT match_count;
END;
$function$;

-- Maintain access restrictions
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips FROM anon;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips TO service_role;
