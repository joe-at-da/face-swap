-- Migration: Create segment_evaluations table for pipeline evaluation
-- This table stores manual evaluations of auto-detected MP identifications

-- Create enum for error reasons
CREATE TYPE segment_evaluation_error_reason AS ENUM (
  'wrong_speaker_detected',  -- Face detection picked wrong person in video
  'wrong_mp_matched'         -- Right person, but matched to wrong MP portrait
);

-- Create segment_evaluations table
CREATE TABLE IF NOT EXISTS segment_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  segment_id UUID NOT NULL REFERENCES event_processing_segments(id) ON DELETE CASCADE,
  evaluated_by UUID NOT NULL REFERENCES auth.users(id),
  is_correct BOOLEAN NOT NULL,
  error_reason segment_evaluation_error_reason,  -- Only set when is_correct = false
  processing_run_id UUID NOT NULL REFERENCES event_processing_runs(id), -- Denormalized for filtering

  -- Locking mechanism for concurrent evaluation
  locked_by UUID REFERENCES auth.users(id),
  locked_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- Constraints
  CONSTRAINT unique_segment_evaluation UNIQUE(segment_id),
  CONSTRAINT error_reason_required_when_incorrect CHECK (
    (is_correct = true AND error_reason IS NULL) OR
    (is_correct = false AND error_reason IS NOT NULL)
  )
);

-- Indexes for performance
CREATE INDEX idx_segment_evaluations_segment_id ON segment_evaluations(segment_id);
CREATE INDEX idx_segment_evaluations_processing_run_id ON segment_evaluations(processing_run_id);
CREATE INDEX idx_segment_evaluations_evaluated_by ON segment_evaluations(evaluated_by);
CREATE INDEX idx_segment_evaluations_is_correct ON segment_evaluations(is_correct);
CREATE INDEX idx_segment_evaluations_locked_by ON segment_evaluations(locked_by) WHERE locked_by IS NOT NULL;
CREATE INDEX idx_segment_evaluations_created_at ON segment_evaluations(created_at);

-- Enable RLS
ALTER TABLE segment_evaluations ENABLE ROW LEVEL SECURITY;

-- Helper function to check if user has @veedoo.io or @veedoo.com email
CREATE OR REPLACE FUNCTION is_veedoo_user(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  v_email TEXT;
BEGIN
  SELECT email INTO v_email FROM auth.users WHERE id = p_user_id;
  RETURN v_email LIKE '%@veedoo.io' OR v_email LIKE '%@veedoo.com';
END;
$$;

-- RLS Policies: Only @veedoo.io / @veedoo.com users can access

-- Veedoo users can view all evaluations
CREATE POLICY "Veedoo users can view evaluations"
ON segment_evaluations
FOR SELECT
TO authenticated
USING (is_veedoo_user((SELECT auth.uid())));

-- Veedoo users can insert evaluations (must be their own)
CREATE POLICY "Veedoo users can insert evaluations"
ON segment_evaluations
FOR INSERT
TO authenticated
WITH CHECK (
  is_veedoo_user((SELECT auth.uid())) AND
  evaluated_by = (SELECT auth.uid())
);

-- Veedoo users can update evaluations (for locking mechanism)
CREATE POLICY "Veedoo users can update evaluations"
ON segment_evaluations
FOR UPDATE
TO authenticated
USING (is_veedoo_user((SELECT auth.uid())))
WITH CHECK (is_veedoo_user((SELECT auth.uid())));

-- Add to realtime publication for live updates
ALTER PUBLICATION supabase_realtime ADD TABLE segment_evaluations;

-- Updated_at trigger (reuse existing function if available)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at') THEN
    CREATE OR REPLACE FUNCTION update_updated_at()
    RETURNS TRIGGER AS $func$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END;
    $func$ LANGUAGE plpgsql;
  END IF;
END;
$$;

CREATE TRIGGER update_segment_evaluations_updated_at
  BEFORE UPDATE ON segment_evaluations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Add comment to describe the table
COMMENT ON TABLE segment_evaluations IS 'Stores manual evaluations of auto-detected MP identifications from video processing pipeline';
COMMENT ON COLUMN segment_evaluations.is_correct IS 'Whether the auto-detected MP identification was correct';
COMMENT ON COLUMN segment_evaluations.error_reason IS 'If incorrect, whether it was wrong speaker detection or wrong MP matching';
COMMENT ON COLUMN segment_evaluations.locked_by IS 'User currently evaluating this segment (for concurrent access)';
COMMENT ON COLUMN segment_evaluations.locked_at IS 'When the segment was locked (locks expire after 2 minutes)';
