import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import { TeamMemberSetupWizard } from "./components/team-member-setup-wizard";
import { Logo } from "@/components/logo";
import { isActualMP } from "@/lib/user-helpers";

export default async function TeamSetupPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // FIRST: If setup is already complete, redirect to dashboard
  // This prevents completed users from entering setup flows
  if (user.user_metadata.is_first_login === false) {
    redirect("/dashboard");
  }

  // SECOND: If user is an actual MP (not just parliament staff) AND not a team member,
  // redirect to mp-setup. MPs who also have team invitations should stay on team-setup.
  const isActualMPUser = await isActualMP(user, supabaseAdminClient);
  const isTeamMember = user.user_metadata?.is_team_member === true || !!user.user_metadata?.invitation_token;
  if (isActualMPUser && !isTeamMember) {
    redirect("/mp-setup");
  }

  // THIRD: Check if user is actually a team member
  const { data: teamMember, error: teamError } = await supabase
    .from("team_members")
    .select("team_id, role, teams(name, description)")
    .eq("user_id", user.id)
    .limit(1)
    .maybeSingle();

  // If user is not a team member, check metadata for recent invitation
  // Don't immediately redirect - they might have just accepted an invitation
  if (!teamMember && !user.user_metadata.is_team_member) {
    // Only redirect to regular setup if we're absolutely certain they're not a team member
    // and there's no invitation token in their metadata
    if (!user.user_metadata.invitation_token && !teamError) {
      console.log("User is not a team member, redirecting to regular setup");
      redirect("/setup");
    }
    // Otherwise, continue - they might be in the process of joining a team
  }

  // If there was an error fetching team member data but user has team metadata,
  // we might be in a race condition where the team member record is being created
  // In this case, provide a fallback
  const teamInfo = teamMember || {
    team_id: user.user_metadata.team_id || "",
    role: user.user_metadata.role || "member",
    teams: {
      name: user.user_metadata.team_name || "Team",
      description: "",
    },
  };

  // Load existing user data for form pre-population
  const existingUserData = {
    firstName: user.user_metadata.first_name || "",
    lastName: user.user_metadata.last_name || "",
    profileImage: user.user_metadata.profile_image || null,
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Logo />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="text-center space-y-2 mb-8">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Welcome to Parliament Connect
          </h2>
          <p className="text-muted-foreground text-lg">
            You&apos;ve been invited to join the{" "}
            <span className="font-semibold">{teamInfo.teams?.name}</span> team
          </p>
        </div>

        <TeamMemberSetupWizard
          initialUserData={existingUserData}
          teamInfo={{
            teamId: teamInfo.team_id,
            teamName: teamInfo.teams?.name || "Team",
            role: teamInfo.role,
          }}
        />
      </main>
    </div>
  );
}
