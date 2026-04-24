-- Remove the member_id overwrite from accept_team_invitation.
-- Previously, accepting a team invitation would overwrite user_roles.member_id
-- with the team owner's member_id. This breaks multi-team support because
-- joining Team B would overwrite the member_id set by Team A.
-- The effective member_id is now resolved dynamically from the team owner
-- via application code (resolveEffectiveMemberId) when browsing team content.

CREATE OR REPLACE FUNCTION accept_team_invitation(p_token VARCHAR, p_user_id UUID)
RETURNS TABLE(success BOOLEAN, message TEXT, team_id UUID, team_name VARCHAR)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_invitation RECORD;
    v_team_name VARCHAR;
BEGIN
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
