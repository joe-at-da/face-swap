import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { acceptInvitationSchema } from "@/schemas/teamSchemas";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

// POST /api/teams/accept-invitation - Accept a team invitation
export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = acceptInvitationSchema.parse(body);

    // Accept the invitation using database function
    const { data: result, error } = await supabase.rpc("accept_team_invitation", {
      p_token: validatedData.token,
      p_user_id: user.id
    });

    if (error) {
      throw error;
    }

    if (!result?.[0]?.success) {
      return NextResponse.json(
        { error: result?.[0]?.message || "Failed to accept invitation" },
        { status: 400 }
      );
    }

    return NextResponse.json({
      message: result[0].message,
      teamId: result[0].team_id,
      teamName: result[0].team_name
    });

  } catch (error) {
    console.error("Accept invitation error:", error);
    return NextResponse.json(
      { error: handleError(error) },
      { status: 500 }
    );
  }
}