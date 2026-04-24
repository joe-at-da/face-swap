-- Optimize hybrid_search_parliament_clips_all to use HNSW indexes:
--
-- The previous version computed GREATEST(...) over two halfvec cosine distances
-- in the semantic CTE, which:
--   1. Forces a sequential scan (GREATEST prevents HNSW index usage)
--   2. Computes each distance twice per row (once in WHERE, once in ORDER BY)
--
-- This version splits the semantic CTE into two separate sub-queries
-- (semantic_transcript and semantic_description), each ordering by a single
-- halfvec <=> distance so the planner can use HNSW indexes. The results are
-- then combined with UNION ALL + GROUP BY, keeping the best similarity per clip.

CREATE OR REPLACE FUNCTION public.hybrid_search_parliament_clips_all(
  query_embedding_text text,
  fulltext_query text,
  target_member_ids integer[] DEFAULT NULL,
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
SET statement_timeout = '15s'
AS $function$
DECLARE
  query_embedding vector(3072);
  candidate_limit integer;
BEGIN
  query_embedding := query_embedding_text::vector(3072);
  candidate_limit := least(match_count * 3, 600);

  RETURN QUERY
  WITH
  -- Sub-query 1: transcript embeddings (HNSW-indexed)
  semantic_transcript AS (
    SELECT pmc.id,
           1 - (pmc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)) AS similarity
    FROM parliament_member_clips pmc
    WHERE (target_member_ids IS NULL OR pmc.member_id = ANY(target_member_ids))
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
    WHERE (target_member_ids IS NULL OR pmc.member_id = ANY(target_member_ids))
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
    LIMIT candidate_limit
  ),

  full_text AS (
    SELECT
      pmc.id,
      ROW_NUMBER() OVER (
        ORDER BY GREATEST(
          COALESCE(ts_rank_cd(
            to_tsvector('english', pmc.transcript),
            websearch_to_tsquery('english', fulltext_query)
          ), 0),
          COALESCE(ts_rank_cd(
            to_tsvector('english', COALESCE(pmc.description, '')),
            websearch_to_tsquery('english', fulltext_query)
          ), 0) * 1.5
        ) DESC
      ) AS rank_ix
    FROM parliament_member_clips pmc
    WHERE
      (target_member_ids IS NULL OR pmc.member_id = ANY(target_member_ids))
      AND pmc.is_deleted = false
      AND pmc.transcript IS NOT NULL
      AND pmc.transcript != ''
      AND (
        to_tsvector('english', pmc.transcript) @@ websearch_to_tsquery('english', fulltext_query)
        OR to_tsvector('english', COALESCE(pmc.description, '')) @@ websearch_to_tsquery('english', fulltext_query)
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
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all FROM anon;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all TO service_role;
