CREATE TABLE public.terms_acceptances (
  user_id uuid PRIMARY KEY
    REFERENCES auth.users(id)
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED,
  accepted_at timestamp with time zone NOT NULL DEFAULT now(),
  accepted_via text NOT NULL CHECK (
    accepted_via IN ('signup', 'invite_signup', 'invite_signin', 'invite_direct')
  )
);

COMMENT ON TABLE public.terms_acceptances IS
'Tracks the first time a user accepted Parliament Connect Terms & Conditions.';

COMMENT ON COLUMN public.terms_acceptances.accepted_via IS
'Which product flow first recorded the user''s Terms & Conditions acceptance.';

GRANT ALL ON TABLE public.terms_acceptances TO postgres;
GRANT ALL ON TABLE public.terms_acceptances TO service_role;
GRANT ALL ON TABLE public.terms_acceptances TO supabase_auth_admin;

-- No RLS policies: access restricted to service_role only (bypasses RLS).
-- If browser-client access is needed later, add user-scoped SELECT policy.
ALTER TABLE public.terms_acceptances ENABLE ROW LEVEL SECURITY;
