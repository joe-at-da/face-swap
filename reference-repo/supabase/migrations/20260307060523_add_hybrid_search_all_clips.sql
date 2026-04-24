-- Add hybrid_search_parliament_clips_all: multi-member variant for admin all-clips page
-- Clones hybrid_search_parliament_clips with target_member_id replaced by target_member_ids integer[]
-- NULL = all members, or a specific set of member IDs
-- Admin access enforced at API route level + REVOKE EXECUTE FROM anon/PUBLIC below

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
  plain_query tsquery;
  or_tsquery tsquery;
BEGIN
  query_embedding := query_embedding_text::vector(3072);
  candidate_limit := least(match_count * 3, 600);

  plain_query := plainto_tsquery('english', fulltext_query);
  IF numnode(plain_query) > 0 THEN
    or_tsquery := replace(plain_query::text, ' & ', ' | ')::tsquery;
  ELSE
    or_tsquery := plain_query;
  END IF;

  RETURN QUERY
  WITH
  semantic AS (
    SELECT
      pmc.id,
      ROW_NUMBER() OVER (
        ORDER BY GREATEST(
          COALESCE(1 - (pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
          COALESCE(1 - (pmc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
        ) DESC
      ) AS rank_ix
    FROM parliament_member_clips pmc
    WHERE
      (target_member_ids IS NULL OR pmc.member_id = ANY(target_member_ids))
      AND pmc.is_deleted = false
      AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
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
      (target_member_ids IS NULL OR pmc.member_id = ANY(target_member_ids))
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

-- Restrict access: revoke default public execute, grant only to authenticated
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all FROM anon;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_parliament_clips_all TO service_role;
