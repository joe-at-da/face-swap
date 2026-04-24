import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import { RecentActivity } from "./components/recent-activity";
import { QuickActions } from "./components/quick-actions";
import { LatestClips } from "./components/latest-clips";
import { isActualMPCached, isTeamOnlyMember } from "@/lib/user-helpers";
import { canAccessInternalAnalytics } from "@/lib/social-analytics-access";

async function getLatestClipsData(userId: string) {
  const supabase = await createSupabaseServerClient();

  // Get user's member_id from user_roles (using admin to bypass RLS)
  const { data: userRole } = await supabaseAdminClient
    .from("user_roles")
    .select("member_id")
    .eq("user_id", userId)
    .single();

  if (!userRole?.member_id) {
    return { clips: [], mpName: "" };
  }

  // Fetch latest 3 parliament member clips by session date
  const { data: clipsData } = await supabase
    .from("parliament_member_clips")
    .select("*")
    .eq("member_id", userRole.member_id)
    .eq("is_deleted", false)
    .not("transcript", "is", null)
    .neq("transcript", "")
    .order("created_at", { ascending: false })
    .limit(100);

  if (!clipsData || clipsData.length === 0) {
    return { clips: [], mpName: "" };
  }

  // Fetch parliament events for session data
  const sessionUids = clipsData
    .map((clip) => clip.session_uid)
    .filter((uid): uid is string => !!uid);

  const parliamentEventsMap = new Map<
    string,
    { session_date: string | null; title: string | null }
  >();

  if (sessionUids.length > 0) {
    const { data: events } = await supabase
      .from("parliament_events")
      .select("event_id, session_date, title")
      .in("event_id", sessionUids)
      .eq("is_deleted", false);

    if (events) {
      events.forEach((event) => {
        if (event.event_id) {
          parliamentEventsMap.set(event.event_id, {
            session_date: event.session_date || null,
            title: event.title || null,
          });
        }
      });
    }
  }

  // Enrich clips with parliament event data
  const enrichedClips = clipsData.map((clip) => ({
    ...clip,
    parliament_event: clip.session_uid
      ? parliamentEventsMap.get(clip.session_uid) || null
      : null,
  }));

  // Sort by session_date (newest first) and take top 3
  const sortedClips = [...enrichedClips]
    .sort((a, b) => {
      const dateA = a.parliament_event?.session_date || a.session_date || a.created_at || "";
      const dateB = b.parliament_event?.session_date || b.session_date || b.created_at || "";
      return new Date(dateB).getTime() - new Date(dateA).getTime();
    })
    .slice(0, 3);

  // Fetch MP name
  const { data: mp } = await supabase
    .from("parliament_members")
    .select("display_name")
    .eq("member_id", userRole.member_id)
    .eq("is_deleted", false)
    .single();

  return {
    clips: sortedClips,
    mpName: mp?.display_name || "",
  };
}

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Check if user is a team-only member (joined via invitation, not an actual MP)
  const isActualMPUser = await isActualMPCached(user?.id || "", user?.email || "", supabaseAdminClient);
  const isUserTeamOnly = isTeamOnlyMember(user, isActualMPUser);

  // If user is a team-only member, redirect them to their team dashboard
  if (isUserTeamOnly) {
    // Get their teams
    const { data: teamMember } = await supabase
      .from("team_members")
      .select("team_id, role, teams(name)")
      .eq("user_id", user?.id || "")
      .order("joined_at", { ascending: true })
      .limit(1)
      .maybeSingle();

    if (teamMember?.team_id) {
      redirect(`/dashboard/teams/${teamMember.team_id}`);
    } else {
      // Team member has no team - they were likely removed
      redirect("/no-team-access");
    }
  }

  // Fetch latest clips data
  const { clips, mpName } = await getLatestClipsData(user?.id || "");
  const canAccessAnalytics = canAccessInternalAnalytics(user?.email);

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1
          className="text-2xl font-bold text-foreground tracking-tight pt-4"
          style={{ fontFamily: "var(--font-family-sans, Inter)" }}
        >
          Parliamentary Dashboard
        </h1>
        <p className="text-base text-muted-foreground font-normal leading-relaxed">
          Access your parliamentary content tools and monitor your digital
          engagement activities.
        </p>
      </div>

      <LatestClips clips={clips} mpName={mpName} />

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-8">
          <QuickActions canAccessAnalytics={canAccessAnalytics} />
        </div>
        <div className="space-y-8">
          <RecentActivity />
        </div>
      </div>
    </div>
  );
}
