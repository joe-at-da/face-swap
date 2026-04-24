-- Add transcript_manually_edited flag to track user-edited transcripts
-- When true, display shows raw DB transcript (user's version)
-- When false (default), display applies fixTranscriptCapitalization()

ALTER TABLE parliament_member_clips
  ADD COLUMN transcript_manually_edited BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE user_clips
  ADD COLUMN transcript_manually_edited BOOLEAN NOT NULL DEFAULT false;
