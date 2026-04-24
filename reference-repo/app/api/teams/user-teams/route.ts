import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

// GET /api/teams/user-teams - Get all teams for current user
export async function GET() {
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

    // Get user's teams using the database function
    const { data: teams, error } = await supabase.rpc("get_user_teams", {
      p_user_id: user.id
    });

    if (error) {
      throw error;
    }

    // Transform the data to match our TeamWithRole interface
    const transformedTeams = teams?.map(team => ({
      id: team.team_id,
      name: team.team_name,
      description: team.team_description,
      owner_id: team.is_owner ? user.id : undefined,
      created_at: team.joined_at,
      updated_at: team.joined_at,
      deleted_at: null,
      is_deleted: false,
      userRole: team.user_role,
    })) || [];

    return NextResponse.json({ teams: transformedTeams });

  } catch (error) {
    console.error("Get user teams error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams/user-teams",
        action: "GET",
        route: "/api/teams/user-teams",
      }) },
      { status: 500 }
    );
  }
}