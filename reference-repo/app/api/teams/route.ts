import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { createTeamSchema } from "@/schemas/teamSchemas";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";
import { isActualMP } from "@/lib/user-helpers";

// GET /api/teams - Get all teams for current user
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
    console.error("Get teams error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams",
        action: "GET",
        route: "/api/teams",
      }) },
      { status: 500 }
    );
  }
}

// POST /api/teams - Create a new team
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
    // Check if user is an actual MP - only MPs can create teams
    const isMP = await isActualMP(user, supabaseAdminClient);
    if (!isMP) {
      return NextResponse.json(
        { error: "Only MPs can create teams" },
        { status: 403 }
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = createTeamSchema.parse(body);

    // Create the team
    const { data: team, error: teamError } = await supabase
      .from("teams")
      .insert({
        name: validatedData.name,
        description: validatedData.description,
        owner_id: user.id,
      })
      .select()
      .single();

    if (teamError) {
      throw teamError;
    }

    // The database trigger 'add_owner_as_member' will automatically add the owner as a team member
    // No need to manually insert the team member here

    return NextResponse.json({
      message: "Team created successfully",
      team
    });

  } catch (error) {
    console.error("Create team error:", error);

    // Get user for context - may fail if error happened before auth
    let userId: string | undefined;
    try {
      const supabase = await createSupabaseServerClient();
      const { data: { user } } = await supabase.auth.getUser();
      userId = user?.id;
    } catch {
      // Ignore - user context is optional for error logging
    }

    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams",
        action: "POST",
        userId,
        route: "/api/teams",
      }) },
      { status: 500 }
    );
  }
}