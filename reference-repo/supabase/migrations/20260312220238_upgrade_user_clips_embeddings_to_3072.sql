-- Upgrade user_clips embedding columns from vector(1536) to vector(3072)
-- for text-embedding-3-large native dimensions (best quality).
--
-- Mirrors the parliament_member_clips upgrade in 20260225053351.
-- pgvector 0.8.0: vector index limit is 2000 dims, halfvec index limit is 4000 dims.
-- Strategy: store as vector(3072) for full float32 precision,
--           index via halfvec(3072) expression cast for HNSW ANN search.
-- Existing 1536-dim embeddings are cleared since they can't be cast to 3072.

-- 1. Drop existing IVFFlat indexes (can't alter column with index present)
DROP INDEX IF EXISTS idx_user_clips_description_embedding;
DROP INDEX IF EXISTS idx_user_clips_title_embedding;

-- 2. Clear existing embeddings (can't cast 1536 -> 3072), then resize columns
UPDATE user_clips SET transcript_embedding = NULL, description_embedding = NULL, title_embedding = NULL;

ALTER TABLE user_clips ALTER COLUMN transcript_embedding TYPE vector(3072);
ALTER TABLE user_clips ALTER COLUMN description_embedding TYPE vector(3072);
ALTER TABLE user_clips ALTER COLUMN title_embedding TYPE vector(3072);

-- 3. Create HNSW indexes using halfvec expression cast (supports up to 4000 dims)
--    HNSW provides better recall than IVFFlat and doesn't need training data.
CREATE INDEX idx_user_clips_transcript_embedding_hnsw
  ON user_clips
  USING hnsw ((transcript_embedding::halfvec(3072)) halfvec_cosine_ops);

CREATE INDEX idx_user_clips_description_embedding_hnsw
  ON user_clips
  USING hnsw ((description_embedding::halfvec(3072)) halfvec_cosine_ops);

CREATE INDEX idx_user_clips_title_embedding_hnsw
  ON user_clips
  USING hnsw ((title_embedding::halfvec(3072)) halfvec_cosine_ops);

-- 4. Update search_user_clips_by_embedding to use vector(3072) + halfvec distance
--    Replace the text-similarity placeholder with proper embedding cosine similarity.
CREATE OR REPLACE FUNCTION search_user_clips_by_embedding(
  query_embedding_text text,
  target_user_id uuid,
  match_limit integer DEFAULT 50,
  match_threshold float DEFAULT 0.78
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
DECLARE
  query_embedding vector(3072);
BEGIN
  query_embedding := query_embedding_text::vector(3072);

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
    uc.transcript,
    pmc.session_date,
    pmc.session_type,
    pmc.debate_topic,
    GREATEST(
      COALESCE(1 - (uc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.title_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
    )::float AS similarity_score,
    jsonb_build_object(
      'id', pmc.id,
      'member_id', pmc.member_id,
      'parliament_members', jsonb_build_object(
        'display_name', pm.display_name,
        'party_name', pm.party_name,
        'party_abbreviation', pm.party_abbreviation
      )
    ) AS parliament_member_clips
  FROM user_clips uc
  INNER JOIN parliament_member_clips pmc ON uc.clip_id = pmc.id
  INNER JOIN parliament_members pm ON pmc.member_id = pm.member_id
  WHERE
    uc.user_id = target_user_id
    AND uc.is_deleted = false
    AND pmc.is_deleted = false
    AND (uc.description_embedding IS NOT NULL OR uc.transcript_embedding IS NOT NULL OR uc.title_embedding IS NOT NULL)
    AND GREATEST(
      COALESCE(1 - (uc.description_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.transcript_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0),
      COALESCE(1 - (uc.title_embedding::halfvec(3072) <=> query_embedding::halfvec(3072)), 0)
    ) >= match_threshold
  ORDER BY similarity_score DESC
  LIMIT match_limit;
END;
$$;

-- 5. Re-grant permissions on updated function
GRANT EXECUTE ON FUNCTION search_user_clips_by_embedding(text, uuid, integer, float)
  TO service_role;

-- 6. Trigger embedding regeneration for all user clips with transcripts.
-- The auto_generate_user_clip_embedding trigger fires on UPDATE of transcript
-- when transcript_embedding IS NULL, calling /api/embeddings/transcript async.
UPDATE user_clips
SET transcript = transcript, updated_at = NOW()
WHERE transcript IS NOT NULL AND transcript != '';
