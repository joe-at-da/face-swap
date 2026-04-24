import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

// PATCH /api/teams/[teamId]/members/[userId] - Update member role
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string; userId: string }> }
) {
  try {
    const { teamId, userId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Check if user can manage members (owner or administrator)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole || userRole === "user") {
      return NextResponse.json(
        { error: "Only team owners and administrators can manage members" },
        { status: 403 }
      );
    }

    // Parse request body
    const body = await request.json();
    const { role } = body;

    // Check if target user is the team owner
    const { data: team } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (!team) {
      return NextResponse.json(
        { error: "Team not found" },
        { status: 404 }
      );
    }

    if (userId === team.owner_id) {
      return NextResponse.json(
        { error: "Cannot change the team owner's role" },
        { status: 400 }
      );
    }

    // Administrators can only update users to user role
    if (userRole === "administrator" && role === "administrator") {
      return NextResponse.json(
        { error: "Administrators can only set user roles, not administrator roles" },
        { status: 403 }
      );
    }

    // Update the member's role
    const { error: updateError } = await supabase
      .from("team_members")
      .update({ role })
      .eq("team_id", teamId)
      .eq("user_id", userId);

    if (updateError) {
      throw updateError;
    }

    return NextResponse.json({
      message: "Member role updated successfully"
    });

  } catch (error) {
    console.error("Update member role error:", error);
    return NextResponse.json(
      { error: handleError(error) },
      { status: 500 }
    );
  }
}

// DELETE /api/teams/[teamId]/members/[userId] - Remove team member
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string; userId: string }> }
) {
  try {
    const { teamId, userId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // User can remove themselves
    if (userId === user.id) {
      // Check if user is the owner
      const { data: team } = await supabase
        .from("teams")
        .select("owner_id")
        .eq("id", teamId)
        .single();

      if (team?.owner_id === user.id) {
        return NextResponse.json(
          { error: "Team owner cannot leave the team. Transfer ownership first." },
          { status: 400 }
        );
      }

      // Remove the user from the team
      const { error: deleteError } = await supabase
        .from("team_members")
        .delete()
        .eq("team_id", teamId)
        .eq("user_id", user.id);

      if (deleteError) {
        throw deleteError;
      }

      // Clear team-related metadata from user if they have no other teams
      const { data: otherTeams } = await supabase
        .from("team_members")
        .select("team_id")
        .eq("user_id", user.id);

      // If user has no other teams, clear the is_team_member flag
      if (!otherTeams || otherTeams.length === 0) {
        const { error: metadataError } = await supabaseAdminClient.auth.admin.updateUserById(
          user.id,
          {
            user_metadata: {
              is_team_member: false,
              team_id: null,
              team_name: null,
              role: null,
              invitation_token: null,
            }
          }
        );

        if (metadataError) {
          console.error("Failed to clear user metadata:", metadataError);
          // Don't throw - user is already removed from team
        }
      }

      return NextResponse.json({
        message: "Successfully left the team"
      });
    }

    // Check if user can remove members (owner or administrator)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId
    });

    if (!userRole || userRole === "user") {
      return NextResponse.json(
        { error: "Only team owners and administrators can remove members" },
        { status: 403 }
      );
    }

    // Check target member's role
    const { data: targetMember } = await supabase
      .from("team_members")
      .select("role")
      .eq("team_id", teamId)
      .eq("user_id", userId)
      .single();

    if (!targetMember) {
      return NextResponse.json(
        { error: "Member not found" },
        { status: 404 }
      );
    }

    // Administrators can only remove users, not other administrators or owners
    if (userRole === "administrator" && targetMember.role !== "user") {
      return NextResponse.json(
        { error: "Administrators can only remove users" },
        { status: 403 }
      );
    }

    // Check if target is the owner
    const { data: team } = await supabase
      .from("teams")
      .select("owner_id")
      .eq("id", teamId)
      .single();

    if (userId === team?.owner_id) {
      return NextResponse.json(
        { error: "Cannot remove the team owner" },
        { status: 400 }
      );
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

    // Clear team-related metadata from user
    // Check if user has any other team memberships
    const { data: otherTeams } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", userId);

    // If user has no other teams, clear the is_team_member flag
    if (!otherTeams || otherTeams.length === 0) {
      const { error: metadataError } = await supabaseAdminClient.auth.admin.updateUserById(
        userId,
        {
          user_metadata: {
            is_team_member: false,
            team_id: null,
            team_name: null,
            role: null,
            invitation_token: null,
          }
        }
      );

      if (metadataError) {
        console.error("Failed to clear user metadata:", metadataError);
        // Don't throw - user is already removed from team
      }
    }

    return NextResponse.json({
      message: "Member removed successfully"
    });

  } catch (error) {
    console.error("Remove member error:", error);
    return NextResponse.json(
      { error: handleError(error) },
      { status: 500 }
    );
  }
}