import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";

// Force this route to use Node.js runtime for postgres compatibility
export const runtime = "nodejs";

// GET /api/teams/invitation/[token] - Get invitation details
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  try {
    const { token } = await params;

    if (!token) {
      return NextResponse.json(
        { error: "Invalid invitation link" },
        { status: 400 }
      );
    }

    // Fetch invitation details with related data using admin client (bypasses RLS for public access)
    const { data: invitation, error } = await supabaseAdminClient
      .from("team_invitations")
      .select(
        `
        id,
        email,
        role,
        expires_at,
        accepted_at,
        team_id,
        invited_by,
        teams!inner (
          id,
          name,
          description,
          owner_id
        )
      `
      )
      .eq("token", token)
      .single();

    if (error || !invitation) {
      console.error("Invitation fetch error:", error);
      return NextResponse.json(
        { error: "Invalid or expired invitation" },
        { status: 404 }
      );
    }

    // Check if invitation is valid
    if (invitation.accepted_at) {
      return NextResponse.json(
        { error: "This invitation has already been accepted" },
        { status: 400 }
      );
    }

    const expiryDate = new Date(invitation.expires_at);
    if (expiryDate < new Date()) {
      return NextResponse.json(
        { error: "This invitation has expired" },
        { status: 400 }
      );
    }

    // Get team owner details using admin client (bypasses RLS)
    const { data: ownerRole } = await supabaseAdminClient
      .from("user_roles")
      .select("email, username")
      .eq("user_id", invitation.teams.owner_id)
      .single();

    // Get owner auth user for metadata (first_name, last_name)
    const {
      data: { user: ownerAuth },
    } = await supabaseAdminClient.auth.admin.getUserById(
      invitation.teams.owner_id
    );

    // Get inviter details using admin client (bypasses RLS)
    const { data: inviterRole } = await supabaseAdminClient
      .from("user_roles")
      .select("email, username")
      .eq("user_id", invitation.invited_by)
      .single();

    // Get inviter auth user for metadata (first_name, last_name)
    const {
      data: { user: inviterAuth },
    } = await supabaseAdminClient.auth.admin.getUserById(invitation.invited_by);

    const response = {
      invitation: {
        id: invitation.id,
        email: invitation.email,
        role: invitation.role,
        expiresAt: invitation.expires_at,
        team: {
          id: invitation.teams.id,
          name: invitation.teams.name,
          description: invitation.teams.description,
          owner: {
            email: ownerRole?.email || "",
            username: ownerRole?.username || null,
            first_name: ownerAuth?.user_metadata?.first_name || null,
            last_name: ownerAuth?.user_metadata?.last_name || null,
          },
        },
        invitedBy: {
          email: inviterRole?.email || "",
          username: inviterRole?.username || null,
          first_name: inviterAuth?.user_metadata?.first_name || null,
          last_name: inviterAuth?.user_metadata?.last_name || null,
        },
      },
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Get invitation error:", error);
    return NextResponse.json({ error: handleError(error) }, { status: 500 });
  }
}
