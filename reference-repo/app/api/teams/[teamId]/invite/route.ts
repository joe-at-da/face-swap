import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { inviteTeamMemberSchema } from "@/schemas/teamSchemas";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/lib/getErrorMessage";
import { sendTeamInvitationEmail } from "@/lib/mailjet";

// POST /api/teams/[teamId]/invite - Send team invitation
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ teamId: string }> },
) {
  try {
    const { teamId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 },
      );
    }

    // Check if user can invite members (owner or administrator)
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole || userRole === "user") {
      return NextResponse.json(
        { error: "Only team owners and administrators can invite members" },
        { status: 403 },
      );
    }

    // Parse and validate request body
    const body = await request.json();
    const validatedData = inviteTeamMemberSchema.parse(body);

    // Get team details for the invitation email
    const { data: team } = await supabase
      .from("teams")
      .select("name")
      .eq("id", teamId)
      .single();

    if (!team) {
      return NextResponse.json({ error: "Team not found" }, { status: 404 });
    }

    // Generate a unique invitation token
    const tokenData = crypto.randomUUID() + "-" + Date.now().toString(36);

    // Create invitation record using admin client to bypass RLS
    const { data: invitation, error: inviteError } = await supabaseAdminClient
      .from("team_invitations")
      .insert({
        team_id: teamId,
        email: validatedData.email,
        role: validatedData.role,
        token: tokenData,
        invited_by: user.id,
      })
      .select()
      .single();

    if (inviteError) {
      throw inviteError;
    }

    // Generate the invitation URL
    const invitationUrl = `${process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000"}/teams/invite/${tokenData}`;

    // Get inviter's full name from auth metadata
    const { data: authUser } = await supabaseAdminClient.auth.admin.getUserById(
      user.id,
    );
    const inviterName = authUser?.user?.user_metadata?.full_name;

    // Send invitation email via Mailjet
    // Note: We don't fail the invitation if email sending fails
    const emailResult = await sendTeamInvitationEmail({
      recipientEmail: validatedData.email,
      invitationUrl,
      teamName: team.name,
      role: validatedData.role,
      inviterName: inviterName || undefined,
      expiresAt: invitation.expires_at,
    });

    // Log if email failed but continue with success response
    if (!emailResult.success) {
      console.warn(
        `Failed to send invitation email to ${validatedData.email}:`,
        emailResult.error,
      );
    }

    return NextResponse.json({
      message: "Invitation sent successfully",
      invitation: {
        id: invitation.id,
        email: invitation.email,
        role: invitation.role,
        expires_at: invitation.expires_at,
        invitation_url: invitationUrl,
      },
      emailSent: emailResult.success,
    });
  } catch (error) {
    console.error("Invite member error:", error);
    return NextResponse.json({ error: handleError(error) }, { status: 500 });
  }
}

// GET /api/teams/[teamId]/invite - Get pending invitations
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ teamId: string }> },
) {
  try {
    const { teamId } = await params;
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 },
      );
    }

    // Check if user is a member of the team
    const { data: userRole } = await supabase.rpc("get_team_role", {
      p_user_id: user.id,
      p_team_id: teamId,
    });

    if (!userRole) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 });
    }

    // Get pending invitations
    const { data: invitations, error } = await supabase
      .from("team_invitations")
      .select("id, email, role, created_at, expires_at")
      .eq("team_id", teamId)
      .is("accepted_at", null)
      .gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false });

    if (error) {
      throw error;
    }

    return NextResponse.json({ invitations });
  } catch (error) {
    console.error("Get invitations error:", error);
    return NextResponse.json({ error: handleError(error) }, { status: 500 });
  }
}
