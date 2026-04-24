"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { handleError } from "@/lib/getErrorMessage";
import { isActualMP, isTeamOnlyMember } from "@/lib/user-helpers";
import { sendTeamInvitationEmail } from "@/lib/mailjet";
import { invitationActionSchema, memberActionSchema } from "@/schemas/teamSchemas";
import type {
  TeamRole,
  TeamMember,
  PendingInvitation,
  TeamMembersData,
} from "@/types/teams";

/**
 * Load team members and pending invitations from Supabase
 */
export async function loadTeamMembers(teamId: string): Promise<TeamMembersData> {
  const supabase = await createSupabaseServerClient();

  // Get authenticated user
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) {
    throw new Error("Authentication required");
  }

  // Check if user is a member of the team
  const { data: userRole } = await supabase.rpc("get_team_role", {
    p_user_id: user.id,
    p_team_id: teamId
  });

  if (!userRole) {
    // Check if user is a team-only member (not an MP)
    const isActualMPUser = await isActualMP(user, supabaseAdminClient);

    // If they're marked as a team member but have no access to this team,
    // redirect to no-team-access page
    if (isTeamOnlyMember(user, isActualMPUser)) {
      redirect("/no-team-access");
    }

    throw new Error("Access denied");
  }

  // Get team members with their roles
  const { data: members, error: membersError } = await supabase
    .from("team_members")
    .select("id, user_id, role, joined_at")
    .eq("team_id", teamId)
    .order("joined_at", { ascending: true });

  if (membersError) {
    throw membersError;
  }

  // Get user details for all members using admin client (bypasses RLS)
  const userIds = members?.map(m => m.user_id) || [];
  const { data: userRoles } = await supabaseAdminClient
    .from("user_roles")
    .select("user_id, email, username")
    .in("user_id", userIds);

  // Create a map for easy lookup
  const userRoleMap = new Map(userRoles?.map(ur => [ur.user_id, ur]) || []);

  // Get team owner info
  const { data: team } = await supabase
    .from("teams")
    .select("owner_id")
    .eq("id", teamId)
    .single();

  // Get invitations (pending + expired, not accepted) for admins/owners
  let invitationsList: PendingInvitation[] = [];
  if (userRole === "owner" || userRole === "administrator") {
    const { data: invitations } = await supabaseAdminClient
      .from("team_invitations")
      .select("id, email, role, created_at, expires_at, invited_by")
      .eq("team_id", teamId)
      .is("accepted_at", null)
      .order("created_at", { ascending: false })
      .limit(50);

    // Get inviter details using admin client (bypasses RLS)
    const inviterIds = invitations?.map(inv => inv.invited_by).filter(Boolean) || [];
    const { data: inviters } = await supabaseAdminClient
      .from("user_roles")
      .select("user_id, email, username")
      .in("user_id", inviterIds);

    const inviterMap = new Map(inviters?.map(inv => [inv.user_id, inv]) || []);

    const now = new Date();
    invitationsList = invitations?.map(invite => ({
      id: invite.id,
      email: invite.email,
      role: invite.role as Exclude<TeamRole, "owner">,
      invitedAt: invite.created_at || "",
      expiresAt: invite.expires_at,
      invitedBy: inviterMap.get(invite.invited_by)?.email || "Unknown",
      status: new Date(invite.expires_at) < now ? "expired" as const : "pending" as const
    })) || [];
  }

  // Format the members
  const formattedMembers: TeamMember[] = members?.map(member => {
    const userRole = userRoleMap.get(member.user_id);
    return {
      id: member.id,
      userId: member.user_id,
      email: userRole?.email || "",
      username: userRole?.username || null,
      role: member.role,
      joinedAt: member.joined_at || "",
      isOwner: member.user_id === team?.owner_id,
      status: "accepted" as const
    };
  }) || [];

  return {
    members: formattedMembers,
    invitations: invitationsList,
    userRole
  };
}

/**
 * Update a team member's role
 */
export async function updateMemberRole(
  teamId: string,
  userId: string,
  newRole: Exclude<TeamRole, "owner">
) {
  try {
    if (!memberActionSchema.safeParse({ teamId, userId }).success) {
      return { success: false, error: "Invalid parameters" };
    }

    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Authentication required" };
    }

    // Check if user can manage members (owner only for this action)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (userRole !== "owner") {
      return { success: false, error: "Only team owners can update member roles" };
    }

    // Check if target user is the team owner
    const { data: team } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (!team) {
      return { success: false, error: "Team not found" };
    }

    if (userId === team.owner_id) {
      return { success: false, error: "Cannot change the team owner's role" };
    }

    // Update the member's role
    const { error: updateError } = await supabase
      .from("team_members")
      .update({ role: newRole })
      .eq("team_id", teamId)
      .eq("user_id", userId);

    if (updateError) {
      throw updateError;
    }

    revalidatePath(`/dashboard/teams/${teamId}/members`);
    return { success: true };

  } catch (error) {
    console.error("Update member role error:", error);
    return { success: false, error: handleError(error, { action: "updateMemberRole", feature: "teams", route: `/dashboard/teams/${teamId}/members` }) };
  }
}

/**
 * Remove a team member
 */
export async function removeMember(teamId: string, userId: string) {
  try {
    if (!memberActionSchema.safeParse({ teamId, userId }).success) {
      return { success: false, error: "Invalid parameters" };
    }

    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Authentication required" };
    }

    // Check if user can remove members (owner only for this action)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (userRole !== "owner") {
      return { success: false, error: "Only team owners can remove members" };
    }

    // Check target member exists
    const { data: targetMember } = await supabase
      .from("team_members")
      .select("role")
      .eq("team_id", teamId)
      .eq("user_id", userId)
      .single();

    if (!targetMember) {
      return { success: false, error: "Member not found" };
    }

    // Check if target is the owner
    const { data: team } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (userId === team?.owner_id) {
      return { success: false, error: "Cannot remove the team owner" };
    }

    // Remove the member
    const { error: deleteError } = await supabase
      .from("team_members")
      .delete()
      .eq("team_id", teamId)
      .eq("user_id", userId);

    if (deleteError) {
      throw deleteError;
    }

    // Check if the user belongs to any other teams before clearing metadata
    const { data: remainingTeams, error: remainingError } = await supabaseAdminClient
      .from("team_members")
      .select("team_id")
      .eq("user_id", userId)
      .limit(1)
      .maybeSingle();

    if (!remainingError && !remainingTeams) {
      // No other teams — safe to clear team metadata
      await supabaseAdminClient.auth.admin.updateUserById(userId, {
        user_metadata: {
          is_team_member: false,
          team_id: null,
          team_name: null,
        },
      });
    }

    revalidatePath(`/dashboard/teams/${teamId}/members`);
    return { success: true };

  } catch (error) {
    console.error("Remove member error:", error);
    return { success: false, error: handleError(error, { action: "removeMember", feature: "teams", route: `/dashboard/teams/${teamId}/members` }) };
  }
}

/**
 * Resend a team invitation — extends expiry by 7 days and re-sends the email
 */
export async function resendInvitation(
  teamId: string,
  invitationId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    if (!invitationActionSchema.safeParse({ teamId, invitationId }).success) {
      return { success: false, error: "Invalid parameters" };
    }

    const supabase = await createSupabaseServerClient();

    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Authentication required" };
    }

    // Check permissions (owner or administrator)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole || (userRole !== "owner" && userRole !== "administrator")) {
      return { success: false, error: "Only team owners and administrators can resend invitations" };
    }

    // Fetch existing invitation via admin client
    const { data: invitation, error: fetchError } = await supabaseAdminClient
      .from("team_invitations")
      .select("id, email, role, token, team_id, accepted_at, last_resent_at")
      .eq("id", invitationId)
      .single();

    if (fetchError || !invitation) {
      return { success: false, error: "Invitation not found" };
    }

    if (invitation.team_id !== teamId) {
      return { success: false, error: "Access denied" };
    }

    if (invitation.accepted_at) {
      return { success: false, error: "Invitation has already been accepted" };
    }

    // Rate limit: reject if last resent within 60 seconds
    if (invitation.last_resent_at) {
      const cooldownMs = 60_000;
      const elapsed = Date.now() - new Date(invitation.last_resent_at).getTime();
      if (elapsed < cooldownMs) {
        const remaining = Math.ceil((cooldownMs - elapsed) / 1000);
        return { success: false, error: `Please wait ${remaining} seconds before resending` };
      }
    }

    // Prepare new token and expiry (not yet committed to DB)
    const newToken = crypto.randomUUID() + "-" + Date.now().toString(36);
    const newExpiry = new Date();
    newExpiry.setDate(newExpiry.getDate() + 7);

    // Get team name for the email
    const { data: team } = await supabase
      .from("teams")
      .select("name")
      .eq("id", teamId)
      .single();

    // Get inviter name
    const inviterName = user.user_metadata?.full_name;

    // Build invitation URL from new token
    const invitationUrl = `${
      process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000"
    }/teams/invite/${newToken}`;

    // Send email BEFORE updating DB — if email fails, old link stays valid
    const emailResult = await sendTeamInvitationEmail({
      recipientEmail: invitation.email,
      invitationUrl,
      teamName: team?.name || "Unknown Team",
      role: invitation.role,
      inviterName: inviterName || undefined,
      expiresAt: newExpiry.toISOString(),
    });

    if (!emailResult.success) {
      return { success: false, error: "Failed to send invitation email. Please try again." };
    }

    // Email sent successfully — now commit token rotation and expiry to DB
    const { error: updateError } = await supabaseAdminClient
      .from("team_invitations")
      .update({
        expires_at: newExpiry.toISOString(),
        token: newToken,
        last_resent_at: new Date().toISOString(),
      })
      .eq("id", invitationId);

    if (updateError) {
      throw updateError;
    }

    revalidatePath(`/dashboard/teams/${teamId}/members`);
    return { success: true };
  } catch (error) {
    console.error("Resend invitation error:", error);
    return { success: false, error: handleError(error, { action: "resendInvitation", feature: "teams", route: `/dashboard/teams/${teamId}/members` }) };
  }
}

/**
 * Cancel/delete a team invitation
 */
export async function cancelInvitation(
  teamId: string,
  invitationId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    if (!invitationActionSchema.safeParse({ teamId, invitationId }).success) {
      return { success: false, error: "Invalid parameters" };
    }

    const supabase = await createSupabaseServerClient();

    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return { success: false, error: "Authentication required" };
    }

    // Check permissions (owner or administrator)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole || (userRole !== "owner" && userRole !== "administrator")) {
      return { success: false, error: "Only team owners and administrators can cancel invitations" };
    }

    const { error: deleteError } = await supabaseAdminClient
      .from("team_invitations")
      .delete()
      .eq("id", invitationId)
      .eq("team_id", teamId);

    if (deleteError) {
      throw deleteError;
    }

    revalidatePath(`/dashboard/teams/${teamId}/members`);
    return { success: true };
  } catch (error) {
    console.error("Cancel invitation error:", error);
    return { success: false, error: handleError(error, { action: "cancelInvitation", feature: "teams", route: `/dashboard/teams/${teamId}/members` }) };
  }
}