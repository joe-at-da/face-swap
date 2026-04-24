import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { notFound, redirect } from "next/navigation";
import { isActualMPCached, isTeamOnlyMember } from "@/lib/user-helpers";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TeamInformationForm } from "./components/team-information-form";
import { TeamSocialMediaIntegrationStatus } from "./components/team-social-media-integration-status";
import { DeleteTeamSection } from "./components/delete-team-section";

interface TeamSettingsPageProps {
  params: Promise<{
    teamId: string;
  }>;
}

export default async function TeamSettingsPage({ params }: TeamSettingsPageProps) {
  const { teamId } = await params;
  const supabase = await createSupabaseServerClient();

  // Get authenticated user
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) {
    notFound();
  }

  // Get team details
  const { data: team, error: teamError } = await supabase
    .from("teams")
    .select("*")
    .eq("id", teamId)
    .single();

  if (teamError || !team) {
    notFound();
  }

  // Check if user is owner or administrator
  const { data: userRole } = await supabase.rpc("get_team_role", {
    p_user_id: user.id,
    p_team_id: teamId
  });

  if (!userRole || (userRole !== "owner" && userRole !== "administrator")) {
    // Check if user is a team-only member (not an MP)
    const isActualMPUser = await isActualMPCached(user.id, user.email!, supabaseAdminClient);

    // If they're marked as a team member but have no access to this team,
    // redirect to no-team-access page
    if (isTeamOnlyMember(user, isActualMPUser) && !userRole) {
      redirect("/no-team-access");
    }

    notFound();
  }

  // Get team stats for deletion confirmation
  const { count: memberCount } = await supabase
    .from("team_members")
    .select("*", { count: "exact", head: true })
    .eq("team_id", teamId);

  const { count: clipCount } = await supabase
    .from("user_clips")
    .select("*", { count: "exact", head: true })
    .eq("team_id", teamId)
    .eq("is_deleted", false);

  const isOwner = userRole === "owner";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Team Settings</h1>
        <p className="text-muted-foreground">
          Manage settings and preferences for {team.name}
        </p>
      </div>

      {/* Settings Sections */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          {/* Team Information Form */}
          <TeamInformationForm
            teamId={teamId}
            initialName={team.name}
            initialDescription={team.description}
          />

          {/* Team Social Media Integration */}
          <TeamSocialMediaIntegrationStatus
            teamId={teamId}
            teamName={team.name}
          />
        </div>

        <div className="space-y-6">
          {/* Team Preferences */}
          <Card>
            <CardHeader>
              <CardTitle>Team Preferences</CardTitle>
              <CardDescription>
                Configure team-wide preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-muted/50 rounded-lg p-4 border border-border">
                <p className="text-sm text-muted-foreground">
                  Additional team preferences and settings will be available here in future updates.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Team Section - Only show to team owner */}
      {isOwner && (
        <div className="max-w-2xl">
          <DeleteTeamSection
            teamInfo={{
              id: teamId,
              name: team.name,
              memberCount: memberCount ?? 0,
              clipCount: clipCount ?? 0,
            }}
          />
        </div>
      )}
    </div>
  );
}
