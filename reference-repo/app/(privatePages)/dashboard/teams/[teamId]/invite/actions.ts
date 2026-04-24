"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { inviteTeamMemberSchema } from "@/schemas/teamSchemas";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { handleError } from "@/lib/getErrorMessage";
import { sendTeamInvitationEmail } from "@/lib/mailjet";
import { isActualMP, isTeamOnlyMember } from "@/lib/user-helpers";
import type { Database } from "@/supabaseTypes";

type TeamRole = Database["public"]["Enums"]["team_role"];

export interface InvitationResult {
  success: boolean;
  error?: string;
  invitation?: {
    id: string;
    email: string;
    role: string;
    expires_at: string;
    invitation_url: string;
  };
}

/**
 * Check if the current user can invite members to the team
 */
export async function checkInvitePermissions(teamId: string): Promise<{
  canInvite: boolean;
  userRole: TeamRole | null;
}> {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user) {
    return { canInvite: false, userRole: null };
  }

  const roleResult = await supabase.rpc("get_team_role", {
    p_user_id: user.id,
    p_team_id: teamId,
  });
  const userRole = roleResult.data as TeamRole | null;
  const roleError = roleResult.error;

  if (roleError) {
    console.error("Error checking user role:", roleError);
    return { canInvite: false, userRole: null };
  }

  // If no role, check if this is a removed team member
  if (!userRole) {
    const isActualMPUser = await isActualMP(user, supabaseAdminClient);

    if (isTeamOnlyMember(user, isActualMPUser)) {
      redirect("/no-team-access");
    }
  }

  const canInvite = userRole === "owner" || userRole === "administrator";

  return { canInvite, userRole };
}

/**
 * Create a team invitation
 */
export async function createTeamInvitation(
  teamId: string,
  email: string,
  role: "administrator" | "user",
): Promise<InvitationResult> {
  try {
    console.log("[createTeamInvitation] Starting invitation creation for:", {
      teamId,
      email,
      role,
    });
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      console.error("[createTeamInvitation] Auth error:", authError);
      return { success: false, error: "Authentication required" };
    }
    console.log("[createTeamInvitation] Authenticated user:", user.id);

    // Check if user can invite members (owner or administrator)
    const roleResult = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });
    const userRole = roleResult.data as TeamRole | null;
    const roleError = roleResult.error;

    console.log(
      "[createTeamInvitation] User role:",
      userRole,
      "Error:",
      roleError,
    );

    if (roleError) {
      console.error("Error checking user role:", roleError);
      return {
        success: false,
        error: "Failed to verify permissions",
      };
    }

    if (!userRole || userRole === "user") {
      console.log("[createTeamInvitation] Insufficient permissions:", userRole);
      return {
        success: false,
        error: "Only team owners and administrators can invite members",
      };
    }

    // Validate data
    const validatedData = inviteTeamMemberSchema.parse({ email, role });

    // Get team details for the invitation
    const teamResult = await supabase
      .from("teams")
      .select("name")
      .eq("id", teamId)
      .single();
    const team = teamResult.data as { name: string } | null;
    const teamError = teamResult.error;

    if (teamError || !team) {
      console.error("[createTeamInvitation] Team not found:", teamError);
      return { success: false, error: "Team not found" };
    }
    console.log("[createTeamInvitation] Team found:", team.name);

    // Generate a unique invitation token
    const tokenData = crypto.randomUUID() + "-" + Date.now().toString(36);

    console.log(
      "[createTeamInvitation] Creating invitation with token:",
      tokenData,
    );

    // Create invitation record using admin client to bypass RLS
    const { data: invitation, error: inviteError } = await supabaseAdminClient
      .from("team_invitations")
      .insert({
        team_id: teamId,
        email: validatedData.email,
        role: validatedData.role,
        token: tokenData,
        invited_by: user.id,
      })
      .select()
      .single();

    if (inviteError || !invitation) {
      console.error(
        "[createTeamInvitation] Failed to create invitation:",
        inviteError,
      );
      throw inviteError || new Error("Failed to create invitation");
    }
    console.log("[createTeamInvitation] Invitation created:", invitation.id);

    // Generate the invitation URL
    const invitationUrl = `${
      process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000"
    }/teams/invite/${tokenData}`;

    // Get inviter's full name from auth metadata
    const { data: authUser } = await supabaseAdminClient.auth.admin.getUserById(
      user.id,
    );
    const inviterName = authUser?.user?.user_metadata?.full_name;

    // Send invitation email via Mailjet
    // Note: We don't fail the invitation if email sending fails
    const emailResult = await sendTeamInvitationEmail({
      recipientEmail: validatedData.email,
      invitationUrl,
      teamName: team.name,
      role: validatedData.role,
      inviterName: inviterName || undefined,
      expiresAt: invitation.expires_at,
    });

    // Log if email failed but continue with success response
    if (!emailResult.success) {
      console.warn(
        `Failed to send invitation email to ${validatedData.email}:`,
        emailResult.error,
      );
    }

    revalidatePath(`/dashboard/teams/${teamId}/members`);
    revalidatePath(`/dashboard/teams/${teamId}/invite`);

    const result = {
      success: true,
      invitation: {
        id: invitation.id,
        email: invitation.email,
        role: invitation.role,
        expires_at: invitation.expires_at,
        invitation_url: invitationUrl,
      },
    };

    console.log("[createTeamInvitation] Success! Returning result:", result);
    return result;
  } catch (error) {
    console.error("[createTeamInvitation] Error:", error);
    return { success: false, error: handleError(error) };
  }
}
