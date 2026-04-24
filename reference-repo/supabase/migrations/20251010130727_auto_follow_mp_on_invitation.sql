-- Update accept_team_invitation function to automatically follow team owner's MP
-- When a user accepts a team invitation, they should automatically follow the same MP as the team owner

CREATE OR REPLACE FUNCTION accept_team_invitation(p_token VARCHAR, p_user_id UUID)
RETURNS TABLE(success BOOLEAN, message TEXT, team_id UUID, team_name VARCHAR)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_invitation RECORD;
    v_team_name VARCHAR;
    v_team_owner_id UUID;
    v_team_owner_member_id INTEGER;
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

    -- Get team name and owner
    SELECT name, owner_id INTO v_team_name, v_team_owner_id
    FROM teams
    WHERE id = v_invitation.team_id;

    -- Check if user is already a member
    IF is_team_member(v_invitation.team_id, p_user_id) THEN
        RETURN QUERY SELECT FALSE, 'Already a team member', v_invitation.team_id, v_team_name;
        RETURN;
    END IF;

    -- Get the team owner's member_id (the MP they follow)
    SELECT member_id INTO v_team_owner_member_id
    FROM user_roles
    WHERE user_id = v_team_owner_id;

    -- Add user to team
    INSERT INTO team_members (team_id, user_id, role, invited_by)
    VALUES (v_invitation.team_id, p_user_id, v_invitation.role, v_invitation.invited_by);

    -- Mark invitation as accepted
    UPDATE team_invitations
    SET accepted_by = p_user_id, accepted_at = NOW()
    WHERE id = v_invitation.id;

    -- If the team owner follows an MP, set the invited user to follow the same MP
    IF v_team_owner_member_id IS NOT NULL THEN
        UPDATE user_roles
        SET member_id = v_team_owner_member_id
        WHERE user_id = p_user_id;
    END IF;

    RETURN QUERY SELECT TRUE, 'Successfully joined team', v_invitation.team_id, v_team_name;
END;
$$;
