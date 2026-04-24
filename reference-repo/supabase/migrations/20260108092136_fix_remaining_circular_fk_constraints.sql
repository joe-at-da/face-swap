-- Fix Remaining Circular Foreign Key Constraints for pg_dump
-- This migration makes all remaining non-deferrable foreign key constraints deferrable
-- to eliminate pg_dump warnings about circular dependencies during backup operations.

-- ============================================================================
-- CROSS-SCHEMA FOREIGN KEYS TO auth.users (Critical for pg_dump)
-- ============================================================================

-- segment_evaluations.locked_by -> auth.users(id)
ALTER TABLE public.segment_evaluations
DROP CONSTRAINT IF EXISTS segment_evaluations_locked_by_fkey;

ALTER TABLE public.segment_evaluations
ADD CONSTRAINT segment_evaluations_locked_by_fkey
FOREIGN KEY (locked_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT segment_evaluations_locked_by_fkey ON public.segment_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- segment_evaluations.evaluated_by -> auth.users(id)
ALTER TABLE public.segment_evaluations
DROP CONSTRAINT IF EXISTS segment_evaluations_evaluated_by_fkey;

ALTER TABLE public.segment_evaluations
ADD CONSTRAINT segment_evaluations_evaluated_by_fkey
FOREIGN KEY (evaluated_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT segment_evaluations_evaluated_by_fkey ON public.segment_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- portrait_collection_evaluations.evaluated_by -> auth.users(id)
ALTER TABLE public.portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS portrait_collection_evaluations_evaluated_by_fkey;

ALTER TABLE public.portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_evaluated_by_fkey
FOREIGN KEY (evaluated_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT portrait_collection_evaluations_evaluated_by_fkey ON public.portrait_collection_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- portrait_collection_evaluations.locked_by -> auth.users(id)
ALTER TABLE public.portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS portrait_collection_evaluations_locked_by_fkey;

ALTER TABLE public.portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_locked_by_fkey
FOREIGN KEY (locked_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT portrait_collection_evaluations_locked_by_fkey ON public.portrait_collection_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- EVENT PROCESSING SYSTEM FOREIGN KEYS
-- ============================================================================

-- event_processing_runs.event_id -> parliament_events(event_id)
ALTER TABLE public.event_processing_runs
DROP CONSTRAINT IF EXISTS fk_event_processing_runs_event_id;

ALTER TABLE public.event_processing_runs
ADD CONSTRAINT fk_event_processing_runs_event_id
FOREIGN KEY (event_id)
REFERENCES parliament_events(event_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_event_processing_runs_event_id ON public.event_processing_runs IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- event_processing_segments.processing_run_id -> event_processing_runs(id)
ALTER TABLE public.event_processing_segments
DROP CONSTRAINT IF EXISTS fk_segments_processing_run_id;

ALTER TABLE public.event_processing_segments
ADD CONSTRAINT fk_segments_processing_run_id
FOREIGN KEY (processing_run_id)
REFERENCES event_processing_runs(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_segments_processing_run_id ON public.event_processing_segments IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- event_processing_segments.member_id -> parliament_members(member_id)
ALTER TABLE public.event_processing_segments
DROP CONSTRAINT IF EXISTS fk_segments_member_id;

ALTER TABLE public.event_processing_segments
ADD CONSTRAINT fk_segments_member_id
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_segments_member_id ON public.event_processing_segments IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- event_processing_segments.manually_assigned_member_id -> parliament_members(member_id)
ALTER TABLE public.event_processing_segments
DROP CONSTRAINT IF EXISTS fk_segments_manually_assigned_member_id;

ALTER TABLE public.event_processing_segments
ADD CONSTRAINT fk_segments_manually_assigned_member_id
FOREIGN KEY (manually_assigned_member_id)
REFERENCES parliament_members(member_id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_segments_manually_assigned_member_id ON public.event_processing_segments IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- PARLIAMENT MEMBER CLIPS FOREIGN KEYS
-- ============================================================================

-- parliament_member_clips.processing_segment_id -> event_processing_segments(id)
ALTER TABLE public.parliament_member_clips
DROP CONSTRAINT IF EXISTS fk_parliament_member_clips_processing_segment_id;

ALTER TABLE public.parliament_member_clips
ADD CONSTRAINT fk_parliament_member_clips_processing_segment_id
FOREIGN KEY (processing_segment_id)
REFERENCES event_processing_segments(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_parliament_member_clips_processing_segment_id ON public.parliament_member_clips IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- parliament_member_clips.session_uid -> parliament_events(event_id)
ALTER TABLE public.parliament_member_clips
DROP CONSTRAINT IF EXISTS fk_parliament_member_clips_session_uid;

ALTER TABLE public.parliament_member_clips
ADD CONSTRAINT fk_parliament_member_clips_session_uid
FOREIGN KEY (session_uid)
REFERENCES parliament_events(event_id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_parliament_member_clips_session_uid ON public.parliament_member_clips IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- EVALUATION TABLES FOREIGN KEYS
-- ============================================================================

-- portrait_collection_evaluations.processing_run_id -> event_processing_runs(id)
ALTER TABLE public.portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS portrait_collection_evaluations_processing_run_id_fkey;

ALTER TABLE public.portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_processing_run_id_fkey
FOREIGN KEY (processing_run_id)
REFERENCES event_processing_runs(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT portrait_collection_evaluations_processing_run_id_fkey ON public.portrait_collection_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- portrait_collection_evaluations.segment_id -> event_processing_segments(id)
ALTER TABLE public.portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS portrait_collection_evaluations_segment_id_fkey;

ALTER TABLE public.portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_segment_id_fkey
FOREIGN KEY (segment_id)
REFERENCES event_processing_segments(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT portrait_collection_evaluations_segment_id_fkey ON public.portrait_collection_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- portrait_collection_evaluations.member_id_selected -> parliament_members(member_id)
ALTER TABLE public.portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS portrait_collection_evaluations_member_id_selected_fkey;

ALTER TABLE public.portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_member_id_selected_fkey
FOREIGN KEY (member_id_selected)
REFERENCES parliament_members(member_id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT portrait_collection_evaluations_member_id_selected_fkey ON public.portrait_collection_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- segment_evaluations.processing_run_id -> event_processing_runs(id)
ALTER TABLE public.segment_evaluations
DROP CONSTRAINT IF EXISTS segment_evaluations_processing_run_id_fkey;

ALTER TABLE public.segment_evaluations
ADD CONSTRAINT segment_evaluations_processing_run_id_fkey
FOREIGN KEY (processing_run_id)
REFERENCES event_processing_runs(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT segment_evaluations_processing_run_id_fkey ON public.segment_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- segment_evaluations.segment_id -> event_processing_segments(id)
ALTER TABLE public.segment_evaluations
DROP CONSTRAINT IF EXISTS segment_evaluations_segment_id_fkey;

ALTER TABLE public.segment_evaluations
ADD CONSTRAINT segment_evaluations_segment_id_fkey
FOREIGN KEY (segment_id)
REFERENCES event_processing_segments(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT segment_evaluations_segment_id_fkey ON public.segment_evaluations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- SEGMENT PORTRAIT MATCHES FOREIGN KEYS
-- ============================================================================

-- segment_portrait_matches.face_encoding_id -> parliament_member_face_encodings(id)
ALTER TABLE public.segment_portrait_matches
DROP CONSTRAINT IF EXISTS fk_portrait_matches_face_encoding_id;

ALTER TABLE public.segment_portrait_matches
ADD CONSTRAINT fk_portrait_matches_face_encoding_id
FOREIGN KEY (face_encoding_id)
REFERENCES parliament_member_face_encodings(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_portrait_matches_face_encoding_id ON public.segment_portrait_matches IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- segment_portrait_matches.segment_id -> event_processing_segments(id)
ALTER TABLE public.segment_portrait_matches
DROP CONSTRAINT IF EXISTS fk_portrait_matches_segment_id;

ALTER TABLE public.segment_portrait_matches
ADD CONSTRAINT fk_portrait_matches_segment_id
FOREIGN KEY (segment_id)
REFERENCES event_processing_segments(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_portrait_matches_segment_id ON public.segment_portrait_matches IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- segment_portrait_matches.member_id -> parliament_members(member_id)
ALTER TABLE public.segment_portrait_matches
DROP CONSTRAINT IF EXISTS fk_portrait_matches_member_id;

ALTER TABLE public.segment_portrait_matches
ADD CONSTRAINT fk_portrait_matches_member_id
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_portrait_matches_member_id ON public.segment_portrait_matches IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- SEGMENT SPEAKER FACES FOREIGN KEYS
-- ============================================================================

-- segment_speaker_faces.segment_id -> event_processing_segments(id)
ALTER TABLE public.segment_speaker_faces
DROP CONSTRAINT IF EXISTS fk_speaker_faces_segment_id;

ALTER TABLE public.segment_speaker_faces
ADD CONSTRAINT fk_speaker_faces_segment_id
FOREIGN KEY (segment_id)
REFERENCES event_processing_segments(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT fk_speaker_faces_segment_id ON public.segment_speaker_faces IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'All remaining circular foreign key constraints have been made deferrable:';
    RAISE NOTICE '- Cross-schema auth.users references (segment_evaluations, portrait_collection_evaluations)';
    RAISE NOTICE '- Event processing system FKs (event_processing_runs, event_processing_segments)';
    RAISE NOTICE '- Parliament member clips FKs (processing_segment_id, session_uid)';
    RAISE NOTICE '- Evaluation tables FKs (portrait_collection_evaluations, segment_evaluations)';
    RAISE NOTICE '- Segment portrait matches FKs';
    RAISE NOTICE '- Segment speaker faces FKs';
    RAISE NOTICE 'This should resolve all pg_dump circular dependency warnings.';
END $$;
