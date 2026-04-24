-- Create team_role enum (check if exists first)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'team_role') THEN
        CREATE TYPE team_role AS ENUM ('owner', 'administrator', 'user');
    END IF;
END $$;

-- Create teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES auth.users(id),
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create team_members table
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role team_role NOT NULL DEFAULT 'user',
    invited_by UUID REFERENCES auth.users(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- Create team_invitations table
CREATE TABLE IF NOT EXISTS team_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role team_role NOT NULL DEFAULT 'user',
    token VARCHAR(255) NOT NULL UNIQUE,
    invited_by UUID NOT NULL REFERENCES auth.users(id),
    accepted_by UUID REFERENCES auth.users(id),
    accepted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create team_mp_follows table for team-specific MP follows
CREATE TABLE IF NOT EXISTS team_mp_follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id),
    followed_by UUID NOT NULL REFERENCES auth.users(id),
    followed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, member_id)
);

-- Create team_notification_preferences table
CREATE TABLE IF NOT EXISTS team_notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE,
    in_app_notifications BOOLEAN DEFAULT TRUE,
    mp_activity_notifications BOOLEAN DEFAULT TRUE,
    clip_processing_notifications BOOLEAN DEFAULT TRUE,
    team_activity_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- Add team_id to user_clips table for team ownership
ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE SET NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_teams_owner_id ON teams(owner_id) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_teams_is_deleted ON teams(is_deleted);
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team_user ON team_members(team_id, user_id);
CREATE INDEX IF NOT EXISTS idx_team_invitations_token ON team_invitations(token);
CREATE INDEX IF NOT EXISTS idx_team_invitations_email ON team_invitations(email);
CREATE INDEX IF NOT EXISTS idx_team_invitations_team_id ON team_invitations(team_id);
CREATE INDEX IF NOT EXISTS idx_team_mp_follows_team_id ON team_mp_follows(team_id);
CREATE INDEX IF NOT EXISTS idx_team_mp_follows_member_id ON team_mp_follows(member_id);
CREATE INDEX IF NOT EXISTS idx_user_clips_team_id ON user_clips(team_id);

-- Helper function to check if user is a team member (avoids recursion in RLS)
CREATE OR REPLACE FUNCTION is_team_member(p_team_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM team_members
        WHERE team_id = p_team_id
        AND user_id = p_user_id
    );
END;
$$;

-- Helper function to get team role (avoids recursion in RLS)
CREATE OR REPLACE FUNCTION get_team_role(p_team_id UUID, p_user_id UUID)
RETURNS team_role
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role team_role;
BEGIN
    -- Check if user is the owner first
    SELECT 'owner'::team_role INTO v_role
    FROM teams
    WHERE id = p_team_id AND owner_id = p_user_id;

    IF v_role IS NOT NULL THEN
        RETURN v_role;
    END IF;

    -- Check team_members table
    SELECT role INTO v_role
    FROM team_members
    WHERE team_id = p_team_id AND user_id = p_user_id;

    RETURN v_role;
END;
$$;

-- RLS Policies for teams table
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

-- Teams: Users can view teams they belong to
CREATE POLICY "Users can view their teams" ON teams
    FOR SELECT
    USING (
        owner_id = auth.uid()
        OR is_team_member(id, auth.uid())
    );

-- Teams: Only owners can update their teams
CREATE POLICY "Owners can update their teams" ON teams
    FOR UPDATE
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());

-- Teams: Users can create teams (becomes owner)
CREATE POLICY "Users can create teams" ON teams
    FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Teams: Only owners can soft delete teams
CREATE POLICY "Owners can delete their teams" ON teams
    FOR DELETE
    USING (owner_id = auth.uid());

-- RLS Policies for team_members table
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

-- Team members: Team members can view members of their teams
CREATE POLICY "Team members can view team members" ON team_members
    FOR SELECT
    USING (is_team_member(team_id, auth.uid()));

-- Team members: Owners and admins can insert members
CREATE POLICY "Owners and admins can add members" ON team_members
    FOR INSERT
    WITH CHECK (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
    );

-- Team members: Owners and admins can update members (except owner role changes)
CREATE POLICY "Owners and admins can update members" ON team_members
    FOR UPDATE
    USING (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
    )
    WITH CHECK (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
    );

-- Team members: Owners and admins can remove members, users can remove themselves
CREATE POLICY "Manage team member removal" ON team_members
    FOR DELETE
    USING (
        user_id = auth.uid() -- Users can leave teams
        OR get_team_role(team_id, auth.uid()) IN ('owner', 'administrator') -- Admins can remove members
    );

-- RLS Policies for team_invitations table
ALTER TABLE team_invitations ENABLE ROW LEVEL SECURITY;

-- Invitations: Team admins can view invitations
CREATE POLICY "Team admins can view invitations" ON team_invitations
    FOR SELECT
    USING (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
        OR email = (SELECT email FROM auth.users WHERE id = auth.uid())
    );

-- Invitations: Admins can create invitations
CREATE POLICY "Admins can create invitations" ON team_invitations
    FOR INSERT
    WITH CHECK (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
        AND invited_by = auth.uid()
    );

-- Invitations: Admins can delete invitations
CREATE POLICY "Admins can delete invitations" ON team_invitations
    FOR DELETE
    USING (
        get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
    );

-- RLS Policies for team_mp_follows table
ALTER TABLE team_mp_follows ENABLE ROW LEVEL SECURITY;

-- MP follows: Team members can view follows
CREATE POLICY "Team members can view MP follows" ON team_mp_follows
    FOR SELECT
    USING (is_team_member(team_id, auth.uid()));

-- MP follows: Team members can add follows
CREATE POLICY "Team members can add MP follows" ON team_mp_follows
    FOR INSERT
    WITH CHECK (
        is_team_member(team_id, auth.uid())
        AND followed_by = auth.uid()
    );

-- MP follows: Users can remove their own follows, admins can remove any
CREATE POLICY "Manage MP follow removal" ON team_mp_follows
    FOR DELETE
    USING (
        followed_by = auth.uid()
        OR get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')
    );

-- RLS Policies for team_notification_preferences table
ALTER TABLE team_notification_preferences ENABLE ROW LEVEL SECURITY;

-- Notification preferences: Users can view their own preferences
CREATE POLICY "Users can view their notification preferences" ON team_notification_preferences
    FOR SELECT
    USING (user_id = auth.uid());

-- Notification preferences: Users can manage their own preferences
CREATE POLICY "Users can manage their notification preferences" ON team_notification_preferences
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- RLS Policies for user_clips with team support
CREATE POLICY "Team members can view team clips" ON user_clips
    FOR SELECT
    USING (
        user_id = auth.uid() -- Personal clips
        OR (team_id IS NOT NULL AND is_team_member(team_id, auth.uid())) -- Team clips
    );

CREATE POLICY "Team members can create team clips" ON user_clips
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid() -- Personal clips
        OR (team_id IS NOT NULL AND is_team_member(team_id, auth.uid())) -- Team clips
    );

CREATE POLICY "Authorized users can update team clips" ON user_clips
    FOR UPDATE
    USING (
        user_id = auth.uid() -- Personal clips
        OR (team_id IS NOT NULL AND get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')) -- Team clips (admins only)
    )
    WITH CHECK (
        user_id = auth.uid() -- Personal clips
        OR (team_id IS NOT NULL AND get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')) -- Team clips (admins only)
    );

CREATE POLICY "Authorized users can delete team clips" ON user_clips
    FOR DELETE
    USING (
        user_id = auth.uid() -- Personal clips
        OR (team_id IS NOT NULL AND get_team_role(team_id, auth.uid()) IN ('owner', 'administrator')) -- Team clips (admins only)
    );

-- Function to create a team with owner as first member
CREATE OR REPLACE FUNCTION create_team_with_owner()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Automatically add the owner as a team member with owner role
    INSERT INTO team_members (team_id, user_id, role)
    VALUES (NEW.id, NEW.owner_id, 'owner');

    RETURN NEW;
END;
$$;

-- Trigger to add owner as member when team is created
CREATE TRIGGER add_owner_as_member
    AFTER INSERT ON teams
    FOR EACH ROW
    EXECUTE FUNCTION create_team_with_owner();

-- Function to handle team ownership transfer
CREATE OR REPLACE FUNCTION transfer_team_ownership(
    p_team_id UUID,
    p_current_owner_id UUID,
    p_new_owner_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Verify current owner
    IF NOT EXISTS (
        SELECT 1 FROM teams
        WHERE id = p_team_id AND owner_id = p_current_owner_id
    ) THEN
        RAISE EXCEPTION 'Not authorized to transfer ownership';
    END IF;

    -- Verify new owner is a team member
    IF NOT is_team_member(p_team_id, p_new_owner_id) THEN
        RAISE EXCEPTION 'New owner must be a team member';
    END IF;

    -- Update team owner
    UPDATE teams
    SET owner_id = p_new_owner_id, updated_at = NOW()
    WHERE id = p_team_id;

    -- Update roles in team_members
    UPDATE team_members
    SET role = 'administrator', updated_at = NOW()
    WHERE team_id = p_team_id AND user_id = p_current_owner_id;

    UPDATE team_members
    SET role = 'owner', updated_at = NOW()
    WHERE team_id = p_team_id AND user_id = p_new_owner_id;

    RETURN TRUE;
END;
$$;

-- Function to accept team invitation
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
    SELECT name INTO v_team_name FROM teams WHERE id = v_invitation.team_id;

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

-- Function to get user teams with role
CREATE OR REPLACE FUNCTION get_user_teams(p_user_id UUID)
RETURNS TABLE(
    team_id UUID,
    team_name VARCHAR,
    team_description TEXT,
    user_role team_role,
    is_owner BOOLEAN,
    joined_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id AS team_id,
        t.name AS team_name,
        t.description AS team_description,
        COALESCE(tm.role, 'owner'::team_role) AS user_role,
        (t.owner_id = p_user_id) AS is_owner,
        COALESCE(tm.joined_at, t.created_at) AS joined_at
    FROM teams t
    LEFT JOIN team_members tm ON t.id = tm.team_id AND tm.user_id = p_user_id
    WHERE t.owner_id = p_user_id OR tm.user_id = p_user_id
        AND NOT t.is_deleted
    ORDER BY t.created_at DESC;
END;
$$;

-- Function to get team statistics
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
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id) + 1 AS total_members, -- +1 for owner
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id AND role = 'administrator') AS total_administrators,
        (SELECT COUNT(*) FROM team_members WHERE team_id = p_team_id AND role = 'user') AS total_users,
        (SELECT COUNT(*) FROM user_clips WHERE team_id = p_team_id) AS total_clips,
        (SELECT COUNT(*) FROM team_mp_follows WHERE team_id = p_team_id) AS followed_mp_count;
END;
$$;

-- Function to check if user can publish to social media for a team
CREATE OR REPLACE FUNCTION can_publish_to_social(p_team_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role team_role;
BEGIN
    v_role := get_team_role(p_team_id, p_user_id);
    RETURN v_role IN ('owner', 'administrator');
END;
$$;

-- Function to generate unique invitation token
CREATE OR REPLACE FUNCTION generate_invitation_token()
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_token VARCHAR;
BEGIN
    LOOP
        v_token := encode(gen_random_bytes(32), 'hex');
        EXIT WHEN NOT EXISTS (SELECT 1 FROM team_invitations WHERE token = v_token);
    END LOOP;
    RETURN v_token;
END;
$$;

-- Update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_team_members_updated_at
    BEFORE UPDATE ON team_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_team_notification_preferences_updated_at
    BEFORE UPDATE ON team_notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();