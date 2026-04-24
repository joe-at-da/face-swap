-- Create portrait_collection_evaluations table to track MP identification from unidentified segments
-- This supports the portrait collection tool where users identify MPs in segments and add their faces to the portrait database

CREATE TABLE IF NOT EXISTS portrait_collection_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Segment reference (unique - one evaluation per segment)
  segment_id UUID NOT NULL UNIQUE REFERENCES event_processing_segments(id) ON DELETE CASCADE,
  processing_run_id UUID NOT NULL REFERENCES event_processing_runs(id),

  -- Evaluation data
  evaluated_by UUID NOT NULL REFERENCES auth.users(id),
  member_id_selected INTEGER NOT NULL REFERENCES parliament_members(member_id),

  -- Face selection tracking (stored as arrays of face indices)
  selected_face_indices INTEGER[] NOT NULL DEFAULT '{}',
  rejected_face_indices INTEGER[] NOT NULL DEFAULT '{}',

  -- Portrait tracking (UUIDs of portraits added to parliament_member_portraits)
  portraits_added UUID[] NOT NULL DEFAULT '{}',

  -- Real-time locking mechanism for concurrent evaluation
  locked_by UUID REFERENCES auth.users(id),
  locked_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- Constraints
  CONSTRAINT must_select_at_least_one_face CHECK (
    array_length(selected_face_indices, 1) > 0
  )
);

-- Create indexes for performance
CREATE INDEX idx_portrait_collection_segment_id ON portrait_collection_evaluations(segment_id);
CREATE INDEX idx_portrait_collection_processing_run_id ON portrait_collection_evaluations(processing_run_id);
CREATE INDEX idx_portrait_collection_evaluated_by ON portrait_collection_evaluations(evaluated_by);
CREATE INDEX idx_portrait_collection_member_id ON portrait_collection_evaluations(member_id_selected);
CREATE INDEX idx_portrait_collection_locked_by ON portrait_collection_evaluations(locked_by) WHERE locked_by IS NOT NULL;

-- Enable Row Level Security
ALTER TABLE portrait_collection_evaluations ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Only Veedoo team members can access
CREATE POLICY "Veedoo users can view portrait collection evaluations"
ON portrait_collection_evaluations FOR SELECT TO authenticated
USING (is_veedoo_user(auth.uid()));

CREATE POLICY "Veedoo users can insert portrait collection evaluations"
ON portrait_collection_evaluations FOR INSERT TO authenticated
WITH CHECK (is_veedoo_user(auth.uid()) AND evaluated_by = auth.uid());

CREATE POLICY "Veedoo users can update portrait collection evaluations"
ON portrait_collection_evaluations FOR UPDATE TO authenticated
USING (is_veedoo_user(auth.uid()))
WITH CHECK (is_veedoo_user(auth.uid()));

-- Enable realtime for live updates across users
ALTER PUBLICATION supabase_realtime ADD TABLE portrait_collection_evaluations;

-- Create trigger for updated_at
CREATE TRIGGER update_portrait_collection_evaluations_updated_at
  BEFORE UPDATE ON portrait_collection_evaluations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Add comments for documentation
COMMENT ON TABLE portrait_collection_evaluations IS
'Tracks manual MP identification from unidentified segments in the portrait collection tool. Includes locking mechanism for concurrent access.';

COMMENT ON COLUMN portrait_collection_evaluations.selected_face_indices IS
'Array of face_index values that were selected as the correct MP';

COMMENT ON COLUMN portrait_collection_evaluations.rejected_face_indices IS
'Array of face_index values that were rejected (not the MP)';

COMMENT ON COLUMN portrait_collection_evaluations.portraits_added IS
'Array of UUIDs of portraits added to parliament_member_portraits table';

COMMENT ON COLUMN portrait_collection_evaluations.locked_by IS
'User currently evaluating this segment (for concurrent access control)';

COMMENT ON COLUMN portrait_collection_evaluations.locked_at IS
'When the segment was locked (locks expire after 2 minutes)';
