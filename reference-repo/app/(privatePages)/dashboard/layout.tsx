import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import { AppSidebar } from "./components/app-sidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { isActualMPCached, isTeamOnlyMember } from "@/lib/user-helpers";
import { isAdminCached } from "@/lib/admin-helpers";
import { isLiberalDemocratCached, getLDTeamIdsForUser } from "@/lib/liberal-democrat-helpers";
import { canAccessInternalAnalytics } from "@/lib/social-analytics-access";
import { SidebarWrapper } from "./components/sidebar-wrapper";
import { MobileTriggerWrapper } from "./components/mobile-trigger-wrapper";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Only redirect if user hasn't completed setup
  // Check is_first_login explicitly for both true and undefined (new users)
  const isActualMPUser = await isActualMPCached(user.id, user.email!, supabaseAdminClient);

  if (user.user_metadata.is_first_login !== false) {
    // User hasn't completed setup - determine which setup flow they need
    // Check team membership first (takes priority over MP check for parliament staff)
    const { data: teamMember, error: teamError } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", user.id)
      .limit(1)
      .maybeSingle();

    if (
      !teamError &&
      (teamMember ||
        user.user_metadata.is_team_member ||
        user.user_metadata.invitation_token)
    ) {
      redirect("/team-setup");
    } else if (isActualMPUser) {
      redirect("/mp-setup");
    } else {
      redirect("/setup");
    }
  }

  // Check if user is a team-only member but has no team access
  // This handles the case where a user was removed from a team after completing setup
  const isUserTeamOnly = isTeamOnlyMember(user, isActualMPUser);

  if (isUserTeamOnly) {
    const { data: teamMember } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", user.id)
      .limit(1)
      .maybeSingle();

    // If team member metadata exists but no team record found, redirect to no-team-access
    if (!teamMember) {
      redirect("/no-team-access");
    }
  }

  // Get sidebar preference from user metadata (default to expanded/true if not set)
  const sidebarDefaultOpen = user.user_metadata?.sidebar_collapsed !== true;

  const isAdmin = await isAdminCached(user.id, supabaseAdminClient);

  // Run personal LD check and batch team LD check in parallel (2+2 queries
  // total regardless of N teams, instead of the previous 3N+2 pattern).
  const [isLiberalDemocrat, ldTeamIds] = await Promise.all([
    isLiberalDemocratCached(user.id, undefined, supabaseAdminClient),
    getLDTeamIdsForUser(user.id, supabaseAdminClient),
  ]);

  // canCreateTeam delegates to isActualMP — reuse the result to avoid duplicate query
  const userCanCreateTeam = isActualMPUser;
  const userCanAccessAnalytics = canAccessInternalAnalytics(user.email);

  return (
    <SidebarWrapper defaultOpen={sidebarDefaultOpen}>
      <AppSidebar
        user={user}
        canCreateTeam={userCanCreateTeam}
        canAccessAnalytics={userCanAccessAnalytics}
        isMP={isActualMPUser}
        isAdmin={isAdmin}
        isLiberalDemocrat={isLiberalDemocrat}
        ldTeamIds={ldTeamIds}
      />
      <SidebarInset>
        <MobileTriggerWrapper />
        <main className="flex flex-1 flex-col gap-4 p-4 pt-0 my-2.5 overflow-hidden">
          {children}
        </main>
      </SidebarInset>
    </SidebarWrapper>
  );
}
