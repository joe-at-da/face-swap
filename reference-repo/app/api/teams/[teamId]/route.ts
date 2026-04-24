import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { updateTeamSchema } from "@/schemas/teamSchemas";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

// GET /api/teams/[teamId] - Get team details
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string }> }
) {
  try {
    const { teamId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Get team details
    const { data: team, error } = await supabase
      .from("teams")
      .select("*")
      .eq("id", teamId)
      .single();

    if (error || !team) {
      return NextResponse.json(
        { error: "Team not found" },
        { status: 404 }
      );
    }

    // Check if user is a member of the team
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      );
    }

    // Get team stats
    const { data: stats } = await supabase.rpc("get_team_stats", {
      p_team_id: teamId
    });

    return NextResponse.json({
      team: {
        ...team,
        userRole,
        stats: stats?.[0]
      }
    });

  } catch (error) {
    console.error("Get team error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams/[teamId]",
        action: "GET",
        route: "/api/teams/[teamId]",
      }) },
      { status: 500 }
    );
  }
}

// PATCH /api/teams/[teamId] - Update team details
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string }> }
) {
  try {
    const { teamId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Check if user is the team owner
    const { data: team, error: teamError } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      return NextResponse.json(
        { error: "Team not found" },
        { status: 404 }
      );
    }

    if (team.owner_id !== user.id) {
      return NextResponse.json(
        { error: "Only team owners can update team details" },
        { status: 403 }
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = updateTeamSchema.parse(body);

    // Update the team
    const { data: updatedTeam, error: updateError } = await supabase
      .from("teams")
      .update(validatedData)
      .eq("id", teamId)
      .select()
      .single();

    if (updateError) {
      throw updateError;
    }

    return NextResponse.json({
      message: "Team updated successfully",
      team: updatedTeam
    });

  } catch (error) {
    console.error("Update team error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams/[teamId]",
        action: "PATCH",
        route: "/api/teams/[teamId]",
      }) },
      { status: 500 }
    );
  }
}

// DELETE /api/teams/[teamId] - Delete a team
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string }> }
) {
  try {
    const { teamId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Check if user is the team owner
    const { data: team, error: teamError } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (teamError || !team) {
      return NextResponse.json(
        { error: "Team not found" },
        { status: 404 }
      );
    }

    if (team.owner_id !== user.id) {
      return NextResponse.json(
        { error: "Only team owners can delete teams" },
        { status: 403 }
      );
    }

    // Soft delete the team
    const { error: deleteError } = await supabase
      .from("teams")
      .update({ is_deleted: true, deleted_at: new Date().toISOString() })
      .eq("id", teamId);

    if (deleteError) {
      throw deleteError;
    }

    return NextResponse.json({
      message: "Team deleted successfully"
    });

  } catch (error) {
    console.error("Delete team error:", error);
    return NextResponse.json(
      { error: handleError(error, {
        component: "api/teams/[teamId]",
        action: "DELETE",
        route: "/api/teams/[teamId]",
      }) },
      { status: 500 }
    );
  }
}