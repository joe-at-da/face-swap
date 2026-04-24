import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";
import { ErrorLogger } from "@/lib/errorLogger";

export async function POST() {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      ErrorLogger.logAuthError(
        authError || new Error("User not authenticated"),
        "setup_complete_auth_check",
        undefined,
        "/api/setup/complete"
      );
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Mark setup as complete in user_roles using admin client
    // Regular users don't have permission to modify user_roles table
    const { error: updateError } = await supabaseAdminClient
      .from("user_roles")
      .update({
        is_first_login: false
      })
      .eq("user_id", user.id);

    if (updateError) {
      ErrorLogger.logDatabaseError(
        updateError,
        "setup_complete_user_roles_update",
        "user_roles",
        user.id
      );
      throw new Error("Failed to update user setup status in database");
    }

    // Also update user metadata
    const { error: metaError } = await supabase.auth.updateUser({
      data: {
        is_first_login: false,
        setup_completed_at: new Date().toISOString(),
      }
    });

    if (metaError) {
      ErrorLogger.logAuthError(
        metaError,
        "setup_complete_metadata_update",
        user.id
      );
      throw new Error("Failed to update user metadata after setup completion");
    }

    return NextResponse.json({
      message: "Setup completed successfully"
    });

  } catch (error) {
    ErrorLogger.logError(
      error instanceof Error ? error : new Error(String(error)),
      {
        action: "setup_complete_general_error",
        route: "/api/setup/complete"
      }
    );
    console.error("Setup completion error:", error);
    const { data: { user } } = await (await createSupabaseServerClient()).auth.getUser();
    return NextResponse.json(
      { error: handleError(error, {
        component: 'api/setup/complete',
        action: 'POST',
        userId: user?.id,
        route: '/api/setup/complete',
      }) },
      { status: 500 }
    );
  }
}