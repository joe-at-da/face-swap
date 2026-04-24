import type { Database } from "@/supabaseTypes";
import type { TestSupabaseAdmin } from "../supabase-admin";

type Tables = Database["public"]["Tables"];
type TeamInsert = Tables["teams"]["Insert"];
type TeamRow = Tables["teams"]["Row"];
type TeamMemberInsert = Tables["team_members"]["Insert"];
type TeamMemberRow = Tables["team_members"]["Row"];
type TeamInvitationInsert = Tables["team_invitations"]["Insert"];
type TeamInvitationRow = Tables["team_invitations"]["Row"];

type CreateTestTeamOpts = Pick<TeamInsert, "owner_id"> &
  Partial<Omit<TeamInsert, "owner_id">>;

export async function createTestTeam(
  admin: TestSupabaseAdmin,
  opts: CreateTestTeamOpts
): Promise<TeamRow> {
  const defaults = {
    name: `E2E Test Team ${Date.now()}`,
    is_deleted: false,
  } satisfies Partial<TeamInsert>;

  const { data, error } = await admin
    .from("teams")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error) throw new Error(`createTestTeam: ${error.message}`);
  return data;
}

type CreateTestTeamMemberOpts = Pick<
  TeamMemberInsert,
  "team_id" | "user_id"
> &
  Partial<Omit<TeamMemberInsert, "team_id" | "user_id">>;

export async function createTestTeamMember(
  admin: TestSupabaseAdmin,
  opts: CreateTestTeamMemberOpts
): Promise<TeamMemberRow> {
  const defaults = {
    role: "user" as const,
  } satisfies Partial<TeamMemberInsert>;

  const { data, error } = await admin
    .from("team_members")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error) throw new Error(`createTestTeamMember: ${error.message}`);
  return data;
}

type CreateTestTeamInvitationOpts = Pick<
  TeamInvitationInsert,
  "email" | "invited_by" | "team_id" | "token"
> &
  Partial<Omit<TeamInvitationInsert, "email" | "invited_by" | "team_id" | "token">>;

export async function createTestTeamInvitation(
  admin: TestSupabaseAdmin,
  opts: CreateTestTeamInvitationOpts
): Promise<TeamInvitationRow> {
  const defaults = {
    role: "user" as const,
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  } satisfies Partial<TeamInvitationInsert>;

  const { data, error } = await admin
    .from("team_invitations")
    .insert({ ...defaults, ...opts })
    .select()
    .single();

  if (error) throw new Error(`createTestTeamInvitation: ${error.message}`);
  return data;
}

export async function cleanupTestTeamsByIds(
  admin: TestSupabaseAdmin,
  teamIds: string[]
): Promise<void> {
  if (teamIds.length === 0) return;

  const [invitationsResult, membersResult] = await Promise.all([
    admin.from("team_invitations").delete().in("team_id", teamIds),
    admin.from("team_members").delete().in("team_id", teamIds),
  ]);

  if (invitationsResult.error) {
    throw new Error(`cleanupTestTeamsByIds invitations: ${invitationsResult.error.message}`);
  }
  if (membersResult.error) {
    throw new Error(`cleanupTestTeamsByIds members: ${membersResult.error.message}`);
  }

  const teamsResult = await admin.from("teams").delete().in("id", teamIds);
  if (teamsResult.error) {
    throw new Error(`cleanupTestTeamsByIds teams: ${teamsResult.error.message}`);
  }
}

export async function cleanupTestTeamById(
  admin: TestSupabaseAdmin,
  teamId: string
): Promise<void> {
  await cleanupTestTeamsByIds(admin, [teamId]);
}

/**
 * Clean up all E2E test teams (names starting with "E2E").
 */
export async function cleanupTestTeams(
  admin: TestSupabaseAdmin
): Promise<void> {
  // Get team IDs first to delete members
  const { data: teams } = await admin
    .from("teams")
    .select("id")
    .like("name", "E2E%");

  if (teams && teams.length > 0) {
    await cleanupTestTeamsByIds(
      admin,
      teams.map((team) => team.id)
    );
  }
}
