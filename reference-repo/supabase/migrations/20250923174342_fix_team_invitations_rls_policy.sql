-- Fix team_invitations RLS policy to use user_roles table instead of auth.users
-- This resolves the permission denied error when inviting users to teams

-- Drop the existing policy that references auth.users
DROP POLICY IF EXISTS "Team admins can view invitations" ON team_invitations;

-- Recreate the policy using user_roles table for email lookup
CREATE POLICY "Team admins can view invitations" ON team_invitations
    FOR SELECT
    USING (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
        OR email = (SELECT email FROM user_roles WHERE user_id = auth.uid())
    );

-- Also create a helper function for getting user email safely
CREATE OR REPLACE FUNCTION get_user_email(p_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_email TEXT;
BEGIN
    -- Get email from user_roles table
    SELECT email INTO v_email
    FROM user_roles
    WHERE user_id = p_user_id;

    RETURN v_email;
END;
$$;

-- Grant execute permission on the helper function
GRANT EXECUTE ON FUNCTION get_user_email TO authenticated;

-- Add comment explaining the function
COMMENT ON FUNCTION get_user_email IS 'Safely retrieves user email from user_roles table for authenticated users';