-- Add index on email column for parliament_member_contacts
-- Used by isActualMPByEmail() for fast MP detection lookups
CREATE INDEX IF NOT EXISTS idx_parliament_member_contacts_email
  ON parliament_member_contacts(email);
