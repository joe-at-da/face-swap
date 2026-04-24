"use server";

import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { revalidatePath } from "next/cache";
import { z } from "zod";
import { ErrorLogger } from "@/lib/errorLogger";
import { deleteTeamWithCleanup } from "@/lib/teamDeletion";

const updateTeamSchema = z.object({
  name: z.string().min(1, "Team name is required").max(255, "Team name is too long"),
  description: z.string().max(500, "Description is too long").optional(),
});

export async function updateTeamInformation(teamId: string, formData: FormData) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      ErrorLogger.logAuthError(
        authError || new Error("No user found"),
        "update_team_information",
        undefined,
        `/dashboard/teams/${teamId}/settings`
      );
      return { success: false, error: "Unauthorized" };
    }

    // Verify user is owner or administrator
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole || (userRole !== "owner" && userRole !== "administrator")) {
      ErrorLogger.logError(new Error("Insufficient permissions to update team"), {
        userId: user.id,
        action: "update_team_information",
        route: `/dashboard/teams/${teamId}/settings`,
        additionalContext: { teamId, userRole: userRole || "none" },
      });
      return { success: false, error: "You don't have permission to update this team" };
    }

    // Parse and validate input
    const rawData = {
      name: formData.get("name") as string,
      description: formData.get("description") as string || "",
    };

    const validatedData = updateTeamSchema.parse(rawData);

    // Update team
    const { error: updateError } = await supabase
      .from("teams")
      .update({
        name: validatedData.name,
        description: validatedData.description || null,
        updated_at: new Date().toISOString(),
      })
      .eq("id", teamId);

    if (updateError) {
      ErrorLogger.logDatabaseError(
        updateError,
        "update_team_information",
        "teams",
        user.id
      );
      return { success: false, error: "Failed to update team information" };
    }

    // Log successful team update
    ErrorLogger.logEvent("Team information updated", {
      userId: user.id,
      action: "update_team_information",
      route: `/dashboard/teams/${teamId}/settings`,
      additionalContext: { teamId, teamName: validatedData.name },
    });

    // Revalidate the page
    revalidatePath(`/dashboard/teams/${teamId}/settings`);
    revalidatePath(`/dashboard/teams/${teamId}`);

    return { success: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      ErrorLogger.logError(error, {
        action: "update_team_information_validation",
        route: `/dashboard/teams/${teamId}/settings`,
        additionalContext: { teamId, validationErrors: error.issues },
      });
      return {
        success: false,
        error: error.issues[0]?.message || "Validation failed"
      };
    }

    ErrorLogger.logError(error instanceof Error ? error : new Error("Unknown error"), {
      action: "update_team_information",
      route: `/dashboard/teams/${teamId}/settings`,
      additionalContext: { teamId },
    });
    return { success: false, error: "An unexpected error occurred" };
  }
}

export async function deleteTeamAction(teamId: string, confirmationText: string) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      ErrorLogger.logAuthError(
        authError || new Error("No user found"),
        "delete_team",
        undefined,
        `/dashboard/teams/${teamId}/settings`
      );
      return { success: false, error: "Unauthorized" };
    }

    // Get team details and verify ownership
    const { data: team, error: teamError } = await supabase
      .from("teams")
      .select("id, name, owner_id")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      ErrorLogger.logDatabaseError(
        teamError || new Error("Team not found"),
        "delete_team",
        "teams",
        user.id
      );
      return { success: false, error: "Team not found" };
    }

    // Verify user is the owner
    if (team.owner_id !== user.id) {
      ErrorLogger.logError(new Error("Insufficient permissions to delete team"), {
        userId: user.id,
        action: "delete_team",
        route: `/dashboard/teams/${teamId}/settings`,
        additionalContext: { teamId, ownerId: team.owner_id },
      });
      return { success: false, error: "Only team owners can delete teams" };
    }

    // Verify confirmation text matches team name
    if (confirmationText !== team.name) {
      return { success: false, error: "Team name does not match confirmation text" };
    }

    // Perform complete team deletion with cleanup
    const result = await deleteTeamWithCleanup(teamId, user.id);

    if (!result.success) {
      ErrorLogger.logError(new Error(result.error || "Team deletion failed"), {
        userId: user.id,
        action: "delete_team",
        route: `/dashboard/teams/${teamId}/settings`,
        additionalContext: { teamId, teamName: team.name },
      });
      return { success: false, error: result.error || "Failed to delete team" };
    }

    // Log successful team deletion
    ErrorLogger.logEvent("Team deleted", {
      userId: user.id,
      action: "delete_team",
      route: `/dashboard/teams/${teamId}/settings`,
      additionalContext: {
        teamId,
        teamName: team.name,
        membersRemoved: result.membersRemoved,
        accountsDeleted: result.accountsDeleted,
        clipsDeleted: result.clipsDeleted,
      },
    });

    // Revalidate paths so the redirect shows updated data
    revalidatePath("/dashboard");
    revalidatePath("/dashboard/teams");

    // Return success - client will handle redirect and state update
    return { success: true };
  } catch (error) {
    ErrorLogger.logError(error instanceof Error ? error : new Error("Unknown error"), {
      action: "delete_team",
      route: `/dashboard/teams/${teamId}/settings`,
      additionalContext: { teamId },
    });
    return { success: false, error: "An unexpected error occurred during team deletion" };
  }
}
