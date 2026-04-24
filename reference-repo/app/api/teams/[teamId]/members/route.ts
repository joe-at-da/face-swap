import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";
import type { Database } from "@/supabaseTypes";

// GET /api/teams/[teamId]/members - Get team members and pending invitations
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

    // Get team members with their roles
    const { data: members, error: membersError } = await supabase
      .from("team_members")
      .select(`
        id,
        user_id,
        role,
        joined_at
      `)
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

    // Get pending invitations (only for admins/owners)
    let pendingInvitations: Array<{
      id: string;
      email: string;
      role: Database["public"]["Enums"]["team_role"];
      invitedAt: string | null;
      expiresAt: string;
      invitedBy: string;
      status: string;
    }> = [];
    if (userRole === "owner" || userRole === "administrator") {
      const { data: invitations } = await supabase
        .from("team_invitations")
        .select(`
          id,
          email,
          role,
          created_at,
          expires_at,
          accepted_at,
          invited_by
        `)
        .eq("team_id", teamId)
        .is("accepted_at", null)
        .gt("expires_at", new Date().toISOString())
        .order("created_at", { ascending: false });

      // Get inviter details using admin client (bypasses RLS)
      const inviterIds = invitations?.map(inv => inv.invited_by).filter(Boolean) || [];
      const { data: inviters } = await supabaseAdminClient
        .from("user_roles")
        .select("user_id, email, username")
        .in("user_id", inviterIds);

      const inviterMap = new Map(inviters?.map(inv => [inv.user_id, inv]) || []);

      pendingInvitations = invitations?.map(invite => {
        const inviter = inviterMap.get(invite.invited_by);
        return {
          id: invite.id,
          email: invite.email,
          role: invite.role,
          invitedAt: invite.created_at,
          expiresAt: invite.expires_at,
          invitedBy: inviter?.username || inviter?.email || "Unknown",
          status: "pending"
        };
      }) || [];
    }

    // Format the response
    const formattedMembers = members?.map(member => {
      const userRole = userRoleMap.get(member.user_id);
      return {
        id: member.id,
        userId: member.user_id,
        email: userRole?.email || "",
        username: userRole?.username || null,
        role: member.role,
        joinedAt: member.joined_at,
        isOwner: member.user_id === team?.owner_id,
        status: "accepted"
      };
    }) || [];

    return NextResponse.json({
      members: formattedMembers,
      invitations: pendingInvitations
    });

  } catch (error) {
    console.error("Get team members error:", error);
    return NextResponse.json(
      { error: handleError(error) },
      { status: 500 }
    );
  }
}