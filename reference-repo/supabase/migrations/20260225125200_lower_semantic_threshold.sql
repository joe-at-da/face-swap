-- Lower semantic threshold from 0.35 to 0.10
-- Real query embeddings (short strings) produce much lower cosine similarity
-- than expected. Even HyDE-expanded queries for "genocide" only reach ~0.24.
-- The Cohere reranker (relevanceScore >= 0.1) is the real quality filter.
-- This threshold just filters obvious noise (0.04-0.09 range).

CREATE OR REPLACE FUNCTION public.hybrid_search_parliament_clips(
  query_embedding_text text,
  fulltext_query text,
  target_member_id integer,
  match_count integer DEFAULT 50,
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
AS $function$
DECLARE
  query_embedding vector(3072);
  candidate_limit integer;
BEGIN
  query_embedding := query_embedding_text::vector(3072);
  candidate_limit := least(match_count * 3, 200);

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
      pmc.member_id = target_member_id
      AND pmc.is_deleted = false
      AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
      AND GREATEST(
        COALESCE(1 - (pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
        COALESCE(1 - (pmc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
      ) >= 0.10
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
      pmc.member_id = target_member_id
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
