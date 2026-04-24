-- Upgrade parliament_member_clips embedding columns from vector(1536) to vector(3072)
-- for text-embedding-3-large native dimensions (best quality).
--
-- pgvector 0.8.0: vector index limit is 2000 dims, halfvec index limit is 4000 dims.
-- Strategy: store as vector(3072) for full float32 precision,
--           index via halfvec(3072) expression cast for HNSW ANN search.
-- Existing embeddings are cleared since they'll be re-generated with the new model.

-- 1. Drop existing indexes FIRST (can't alter column with index present)
DROP INDEX IF EXISTS idx_parliament_member_clips_transcript_embedding_hnsw;
DROP INDEX IF EXISTS idx_parliament_member_clips_description_embedding;

-- 2. Clear existing embeddings (can't cast 1536 -> 3072), then resize columns
UPDATE parliament_member_clips SET transcript_embedding = NULL, description_embedding = NULL;

ALTER TABLE parliament_member_clips
  ALTER COLUMN transcript_embedding TYPE vector(3072);

ALTER TABLE parliament_member_clips
  ALTER COLUMN description_embedding TYPE vector(3072);

-- 3. Create HNSW indexes using halfvec expression cast (supports up to 4000 dims)
--    HNSW provides better recall than IVFFlat and doesn't need training data.
CREATE INDEX idx_parliament_member_clips_transcript_embedding_hnsw
  ON parliament_member_clips
  USING hnsw ((transcript_embedding::halfvec(3072)) halfvec_cosine_ops);

CREATE INDEX idx_parliament_member_clips_description_embedding_hnsw
  ON parliament_member_clips
  USING hnsw ((description_embedding::halfvec(3072)) halfvec_cosine_ops);

-- 4. Update search_parliament_clips_by_vector to use vector(3072) + halfvec distance
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
  query_embedding vector(3072);
BEGIN
  query_embedding := query_embedding_text::vector(3072);

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
      COALESCE(1 - (pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (pmc.transcript_embedding::halfvec(3072)  <=> query_embedding::halfvec(3072)), 0)
    ) AS similarity_score
  FROM parliament_member_clips pmc
  WHERE
    pmc.member_id = target_member_id
    AND pmc.is_deleted = false
    AND pmc.status = 'completed'
    AND (pmc.description_embedding IS NOT NULL OR pmc.transcript_embedding IS NOT NULL)
    AND GREATEST(
      COALESCE(1 - (pmc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (pmc.transcript_embedding::halfvec(3072)  <=> query_embedding::halfvec(3072)), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- 5. Update hybrid_search_parliament_clips to use vector(3072) + halfvec distance
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
  query_embedding vector(3072);
  candidate_limit integer;
BEGIN
  query_embedding := query_embedding_text::vector(3072);
  candidate_limit := least(match_count, 30) * 2;

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
      AND pmc.status = 'completed'
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

-- 6. Re-grant permissions
GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float)
  TO service_role;
GRANT EXECUTE ON FUNCTION search_parliament_clips_by_vector(text, integer, integer, float)
  TO authenticated;

GRANT EXECUTE ON FUNCTION hybrid_search_parliament_clips(text, text, integer, integer, float, float, integer)
  TO service_role;
GRANT EXECUTE ON FUNCTION hybrid_search_parliament_clips(text, text, integer, integer, float, float, integer)
  TO authenticated;
