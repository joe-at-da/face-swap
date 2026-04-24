-- Add composition_json and editor_version columns to user_clips
-- for the Remotion v2 editor. These store the full composition JSON
-- that gets sent to RunPod for rendering.

ALTER TABLE user_clips
  ADD COLUMN IF NOT EXISTS composition_json jsonb,
  ADD COLUMN IF NOT EXISTS editor_version smallint NOT NULL DEFAULT 1;

-- Index for filtering by editor version
CREATE INDEX IF NOT EXISTS idx_user_clips_editor_version
  ON user_clips (editor_version)
  WHERE editor_version = 2;

COMMENT ON COLUMN user_clips.composition_json IS 'Full Remotion VideoComposition JSON for v2 editor exports';
COMMENT ON COLUMN user_clips.editor_version IS '1 = legacy segment-based editor, 2 = Remotion composition editor';
