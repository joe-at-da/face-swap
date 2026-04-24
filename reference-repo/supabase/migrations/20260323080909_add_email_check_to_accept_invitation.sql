-- Add email verification to accept_team_invitation.
-- Previously, the function only validated the token and expiry but never checked
-- that the accepting user's email matched the invitation email. This was safe in
-- the OTP flow (email constrained by OTP delivery) but is exploitable when
-- allowing direct acceptance for already-authenticated users.

CREATE OR REPLACE FUNCTION accept_team_invitation(p_token VARCHAR, p_user_id UUID)
RETURNS TABLE(success BOOLEAN, message TEXT, team_id UUID, team_name VARCHAR)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    v_invitation RECORD;
    v_team_name VARCHAR;
    v_user_email TEXT;
BEGIN
    -- Verify the caller is the user they claim to be.
    -- auth.uid() is set from the JWT for user-client calls, null for admin/service-role.
    -- This prevents a malicious client from passing another user's UUID via direct RPC.
    IF auth.uid() IS NOT NULL AND auth.uid() != p_user_id THEN
        RETURN QUERY SELECT FALSE, 'User ID mismatch'::TEXT, NULL::UUID, NULL::VARCHAR;
        RETURN;
    END IF;

    -- Find valid invitation
    SELECT * INTO v_invitation
    FROM team_invitations
    WHERE token = p_token
        AND accepted_at IS NULL
        AND expires_at > NOW();

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Invalid or expired invitation', NULL::UUID, NULL::VARCHAR;
        RETURN;
    END IF;

    -- Verify accepting user's email matches invitation email
    SELECT email INTO v_user_email
    FROM auth.users
    WHERE id = p_user_id;

    IF v_user_email IS NULL THEN
        RETURN QUERY SELECT FALSE, 'User not found'::TEXT, NULL::UUID, NULL::VARCHAR;
        RETURN;
    END IF;

    IF LOWER(v_invitation.email) != LOWER(v_user_email) THEN
        RETURN QUERY SELECT FALSE, 'Email does not match invitation'::TEXT, NULL::UUID, NULL::VARCHAR;
        RETURN;
    END IF;

    -- Get team name
    SELECT name INTO v_team_name
    FROM teams
    WHERE id = v_invitation.team_id;

    -- Check if user is already a member
    IF is_team_member(v_invitation.team_id, p_user_id) THEN
        RETURN QUERY SELECT FALSE, 'Already a team member', v_invitation.team_id, v_team_name;
        RETURN;
    END IF;

    -- Add user to team
    INSERT INTO team_members (team_id, user_id, role, invited_by)
    VALUES (v_invitation.team_id, p_user_id, v_invitation.role, v_invitation.invited_by);

    -- Mark invitation as accepted
    UPDATE team_invitations
    SET accepted_by = p_user_id, accepted_at = NOW()
    WHERE id = v_invitation.id;

    RETURN QUERY SELECT TRUE, 'Successfully joined team', v_invitation.team_id, v_team_name;
END;
$$;
