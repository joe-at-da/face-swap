import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { deleteTeamWithCleanup } from "@/lib/teamDeletion";
import { sendAccountDeletionConfirmationEmail } from "@/lib/mailjet";
import { ErrorLogger } from "@/lib/errorLogger";

export async function DELETE(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse request body for confirmation
    let body: {
      confirmation?: string;
      password?: string;
    };

    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { confirmation } = body;

    // Require explicit confirmation
    if (confirmation !== "DELETE_MY_ACCOUNT") {
      return NextResponse.json(
        { error: "Account deletion requires explicit confirmation" },
        { status: 400 }
      );
    }

    const userId = user.id;
    const userEmail = user.email;

    console.log(`[Account Deletion] Starting deletion process for user ${userId} (${userEmail})`);

    // Get user info for email
    const { data: userRole } = await supabaseAdminClient
      .from("user_roles")
      .select("username")
      .eq("user_id", userId)
      .single();

    const userName = userRole?.username || undefined;

    // Step 1: Get all teams owned by user
    const { data: ownedTeams, error: teamsError } = await supabaseAdminClient
      .from("teams")
      .select("id, name")
      .eq("owner_id", userId)
      .eq("is_deleted", false);

    if (teamsError) {
      ErrorLogger.logDatabaseError(teamsError, "delete_account", "teams", userId);
      console.error("Failed to fetch owned teams:", teamsError);
    }

    const teamCount = ownedTeams?.length || 0;

    // Step 2: Delete all owned teams with full cleanup
    if (ownedTeams && ownedTeams.length > 0) {
      console.log(`[Account Deletion] Deleting ${ownedTeams.length} owned teams for ${userId}`);

      for (const team of ownedTeams) {
        console.log(`[Account Deletion] Deleting team ${team.id} (${team.name})`);
        const result = await deleteTeamWithCleanup(team.id, userId);

        if (!result.success) {
          ErrorLogger.logError(new Error(result.error || "Team deletion failed"), {
            userId,
            action: "delete_account_team_cleanup",
            route: "/api/settings/account",
            additionalContext: { teamId: team.id, teamName: team.name },
          });
          console.error(`Failed to delete team ${team.id}:`, result.error);
        } else {
          console.log(`[Account Deletion] Successfully deleted team ${team.id}`);
        }
      }
    }

    // Step 3: Count personal clips before deletion
    const { count: personalClipCount } = await supabaseAdminClient
      .from("user_clips")
      .select("*", { count: "exact", head: true })
      .eq("user_id", userId)
      .is("team_id", null)
      .eq("is_deleted", false);

    const totalClips = personalClipCount || 0;

    // Step 4: Hard delete all personal user clips (team clips already deleted)
    const { error: userClipsError } = await supabaseAdminClient
      .from("user_clips")
      .delete()
      .eq("user_id", userId)
      .is("team_id", null);

    if (userClipsError) {
      ErrorLogger.logDatabaseError(userClipsError, "delete_account", "user_clips", userId);
      console.error("Failed to delete personal user clips:", userClipsError);
    } else {
      console.log(`[Account Deletion] Hard deleted ${totalClips} personal clips for ${userId}`);
    }

    // Step 5: Delete user role/profile data
    const { error: userRoleError } = await supabaseAdminClient
      .from("user_roles")
      .delete()
      .eq("user_id", userId);

    if (userRoleError) {
      ErrorLogger.logDatabaseError(userRoleError, "delete_account", "user_roles", userId);
      console.error("Failed to delete user role:", userRoleError);
    } else {
      console.log(`[Account Deletion] Deleted user role for ${userId}`);
    }

    // Step 6: Send confirmation email (async, don't wait)
    if (userEmail) {
      sendAccountDeletionConfirmationEmail({
        recipientEmail: userEmail,
        recipientName: userName,
        teamCount,
        clipCount: totalClips,
      }).catch((error) => {
        ErrorLogger.logApiError(
          error,
          "/account-deletion-confirmation-email",
          "POST",
          userId
        );
        console.error("Failed to send account deletion confirmation email:", error);
      });
    }

    // Step 7: Delete the auth user account
    const { error: deleteAuthError } = await supabaseAdminClient.auth.admin.deleteUser(
      userId
    );

    if (deleteAuthError) {
      ErrorLogger.logAuthError(deleteAuthError, "delete_account", userId);
      console.error("Failed to delete auth user:", deleteAuthError);
      return NextResponse.json(
        { error: "Failed to complete account deletion" },
        { status: 500 }
      );
    }

    console.log(`[Account Deletion] Successfully deleted account for ${userId} (${userEmail})`);

    // Log successful account deletion
    ErrorLogger.logEvent("Account deleted", {
      userId,
      action: "delete_account",
      route: "/api/settings/account",
      additionalContext: {
        teamsDeleted: teamCount,
        clipsDeleted: totalClips,
        email: userEmail,
      },
    });

    // Return success response
    return NextResponse.json({
      success: true,
      message: "Account successfully deleted",
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Delete account error:", error);

    ErrorLogger.logError(error instanceof Error ? error : new Error("Unknown error"), {
      action: "delete_account",
      route: "/api/settings/account",
    });

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to delete account: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// Get account information for deletion confirmation
export async function GET() {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Get user's data summary for deletion confirmation
    const [userClipsResult, userRoleResult, ownedTeamsResult] = await Promise.allSettled([
      supabaseAdminClient
        .from("user_clips")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id)
        .eq("is_deleted", false),

      supabaseAdminClient
        .from("user_roles")
        .select(`
          parliament_members!inner(display_name)
        `)
        .eq("user_id", user.id)
        .single(),

      supabaseAdminClient
        .from("teams")
        .select("id", { count: "exact", head: true })
        .eq("owner_id", user.id)
        .eq("is_deleted", false)
    ]);

    const clipCount = userClipsResult.status === 'fulfilled' ?
      userClipsResult.value.count || 0 : 0;

    const userRole = userRoleResult.status === 'fulfilled' ?
      userRoleResult.value.data : null;

    const teamCount = ownedTeamsResult.status === 'fulfilled' ?
      ownedTeamsResult.value.count || 0 : 0;

    return NextResponse.json({
      success: true,
      data: {
        user_id: user.id,
        email: user.email,
        created_at: user.created_at,
        profile: userRole ? {
          name: 'Not set', // first_name and last_name don't exist in user_roles table
          following_mp: userRole.parliament_members?.display_name || 'None',
        } : null,
        clips_count: clipCount,
        teams_count: teamCount,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Get account info error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch account info: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}