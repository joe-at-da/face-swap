-- Hybrid search function for parliament_member_clips
-- Combines vector similarity (HyDE embedding) + full-text search (expanded terms) using RRF
-- Follows Supabase official hybrid search pattern: https://supabase.com/docs/guides/ai/hybrid-search

CREATE OR REPLACE FUNCTION hybrid_search_parliament_clips(
  query_embedding_text text,
  fulltext_query text,
  target_member_id integer,
  match_count integer DEFAULT 50,
  semantic_weight float DEFAULT 1.0,
  fulltext_weight float DEFAULT 1.0,
  rrf_k integer DEFAULT 50
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
  hybrid_score float
)
LANGUAGE plpgsql
AS $$
DECLARE
  query_embedding vector(1536);
  candidate_limit integer;
BEGIN
  query_embedding := query_embedding_text::vector(1536);
  candidate_limit := least(match_count, 30) * 2;

  RETURN QUERY
  WITH
  -- Vector similarity search using HyDE embedding
  semantic AS (
    SELECT
      pmc.id,
      ROW_NUMBER() OVER (
        ORDER BY GREATEST(
          COALESCE(1 - (pmc.description_embedding <=> query_embedding), 0),
          COALESCE(1 - (pmc.transcript_embedding <=> query_embedding), 0)
        ) DESC
      ) AS rank_ix
    FROM parliament_member_clips pmc
    WHERE
      pmc.member_id = target_member_id
      AND pmc.is_deleted = false
      AND pmc.status = 'completed'
      AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    ORDER BY rank_ix
    LIMIT candidate_limit
  ),

  -- Full-text search using expanded terms with ts_rank_cd (cover density)
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
      AND pmc.status = 'completed'
      AND pmc.transcript IS NOT NULL
      AND pmc.transcript != ''
      AND (
        to_tsvector('english', pmc.transcript) @@ websearch_to_tsquery('english', fulltext_query)
        OR to_tsvector('english', COALESCE(pmc.description, '')) @@ websearch_to_tsquery('english', fulltext_query)
      )
    ORDER BY rank_ix
    LIMIT candidate_limit
  )

  -- RRF fusion: FULL OUTER JOIN + weighted 1/(k+rank) scoring
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
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION hybrid_search_parliament_clips(text, text, integer, integer, float, float, integer)
  TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_parliament_clips(text, text, integer, integer, float, float, integer)
  TO authenticated;

COMMENT ON FUNCTION hybrid_search_parliament_clips(text, text, integer, integer, float, float, integer) IS
'Hybrid search combining vector similarity (HyDE) and full-text search (expanded terms) using Reciprocal Rank Fusion. Follows Supabase official hybrid search pattern.';
