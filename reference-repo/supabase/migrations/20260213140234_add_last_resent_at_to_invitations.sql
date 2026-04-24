-- Add last_resent_at column to team_invitations for resend rate limiting
ALTER TABLE team_invitations
  ADD COLUMN IF NOT EXISTS last_resent_at TIMESTAMPTZ;
