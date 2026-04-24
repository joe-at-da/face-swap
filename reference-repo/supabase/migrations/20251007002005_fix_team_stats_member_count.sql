-- Fix get_team_stats function to correctly count team members
-- The owner is already in the team_members table via the add_owner_as_member trigger
-- So we should not add +1 to the count

CREATE OR REPLACE FUNCTION get_team_stats(p_team_id UUID)
RETURNS TABLE(
    total_members BIGINT,
    total_administrators BIGINT,
    total_users BIGINT,
    total_clips BIGINT,
    followed_mp_count BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id) AS total_members, -- Removed +1
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id AND role = 'administrator') AS total_administrators,
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id AND role = 'user') AS total_users,
        (SELECT COUNT(*) FROM user_clips WHERE team_id = p_team_id) AS total_clips,
        (SELECT COUNT(*) FROM team_mp_follows WHERE team_id = p_team_id) AS followed_mp_count;
END;
$$;
