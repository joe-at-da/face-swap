import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { notFound, redirect } from "next/navigation";
import { isActualMPCached, isTeamOnlyMember } from "@/lib/user-helpers";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Video, UserPlus, Settings, Crown, Shield, User, Eye } from "lucide-react";
import Link from "next/link";
import { LatestClips } from "@/app/(privatePages)/dashboard/components/latest-clips";

async function getTeamLatestClipsData(teamOwnerId: string) {
  const supabase = await createSupabaseServerClient();

  // Get the team owner's member_id from user_roles
  const { data: ownerRole } = await supabaseAdminClient
    .from("user_roles")
    .select("member_id")
    .eq("user_id", teamOwnerId)
    .single();

  if (!ownerRole?.member_id) {
    return { clips: [], mpName: "" };
  }

  // Fetch latest parliament member clips
  const { data: clipsData } = await supabase
    .from("parliament_member_clips")
    .select("*")
    .eq("member_id", ownerRole.member_id)
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
    .eq("member_id", ownerRole.member_id)
    .eq("is_deleted", false)
    .single();

  return {
    clips: sortedClips,
    mpName: mp?.display_name || "",
  };
}

interface TeamDashboardPageProps {
  params: Promise<{
    teamId: string;
  }>;
}

export default async function TeamDashboardPage({ params }: TeamDashboardPageProps) {
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

  // Check if user is a member
  const { data: userRole } = await supabase.rpc("get_team_role", {
    p_user_id: user.id,
    p_team_id: teamId
  });

  if (!userRole) {
    // Check if user is a team-only member (not an actual MP)
    const isActualMPUser = await isActualMPCached(user.id, user.email!, supabaseAdminClient);

    // If they're marked as a team member but have no access to this team,
    // redirect to no-team-access page
    if (isTeamOnlyMember(user, isActualMPUser)) {
      redirect("/no-team-access");
    }

    // Otherwise, it's a regular 404
    notFound();
  }

  // Get team stats
  const { data: stats } = await supabase.rpc("get_team_stats", {
    p_team_id: teamId
  });

  const teamStats = stats?.[0] || {
    total_members: 0,
    total_clips: 0,
    total_administrators: 0,
    total_users: 0,
    followed_mp_count: 0,
  };

  // Get team owner's member_id from user_roles using admin client
  let parliamentMemberClipsCount = 0;
  if (team.owner_id) {
    const { data: ownerRole } = await supabaseAdminClient
      .from("user_roles")
      .select("member_id")
      .eq("user_id", team.owner_id)
      .single();

    if (ownerRole?.member_id) {
      // Count parliament member clips for the team owner's MP
      const { count } = await supabaseAdminClient
        .from("parliament_member_clips")
        .select("*", { count: "exact", head: true })
        .eq("member_id", ownerRole.member_id)
        .eq("is_deleted", false);

      parliamentMemberClipsCount = count || 0;
    }
  }

  // Fetch latest clips for the team owner's MP
  const { clips, mpName } = await getTeamLatestClipsData(team.owner_id);

  // Get role icon and color
  const getRoleBadge = (role: string) => {
    switch (role) {
      case "owner":
        return { icon: Crown, color: "bg-yellow-500", label: "Owner" };
      case "administrator":
        return { icon: Shield, color: "bg-blue-500", label: "Administrator" };
      default:
        return { icon: User, color: "bg-gray-500", label: "Member" };
    }
  };

  const roleInfo = getRoleBadge(userRole);

  return (
    <div className="space-y-6">
      {/* Team Header */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{team.name}</h1>
            {team.description && (
              <p className="text-muted-foreground mt-2">{team.description}</p>
            )}
          </div>
          <Badge className="flex items-center gap-1">
            <roleInfo.icon className="h-3 w-3" />
            {roleInfo.label}
          </Badge>
        </div>
      </div>

      {/* Latest Clips */}
      <LatestClips clips={clips} mpName={mpName} />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Members</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{teamStats.total_members}</div>
            <p className="text-xs text-muted-foreground">
              {teamStats.total_administrators + 1} admin{(teamStats.total_administrators + 1) !== 1 ? "s" : ""}, {teamStats.total_users} user{teamStats.total_users !== 1 ? "s" : ""}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Clips</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{teamStats.total_clips}</div>
            <p className="text-xs text-muted-foreground">Created by team</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">MP Clips Available</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{parliamentMemberClipsCount}</div>
            <p className="text-xs text-muted-foreground">From followed MPs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Created</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {team.created_at
                ? new Date(team.created_at).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short"
                  })
                : "N/A"
              }
            </div>
            <p className="text-xs text-muted-foreground">
              {team.created_at
                ? new Date(team.created_at).getFullYear()
                : ""
              }
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-5 w-5" />
              Create Team Clip
            </CardTitle>
            <CardDescription>
              Create a clip that will belong to your team and persist even if you leave
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href={`/dashboard/create-clips?teamId=${teamId}`}>Create Clip</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              View Team Clips
            </CardTitle>
            <CardDescription>
              Browse and manage all clips created by your team
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href={`/dashboard/teams/${teamId}/clips`}>View Clips</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Manage Members
            </CardTitle>
            <CardDescription>
              View team members and manage their roles
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="outline">
              <Link href={`/dashboard/teams/${teamId}/members`}>View Members</Link>
            </Button>
          </CardContent>
        </Card>

        {(userRole === "owner" || userRole === "administrator") && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Invite Members
              </CardTitle>
              <CardDescription>
                Send invitations to new team members
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full" variant="outline">
                <Link href={`/dashboard/teams/${teamId}/invite`}>Invite Members</Link>
              </Button>
            </CardContent>
          </Card>
        )}

        {userRole === "owner" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Team Settings
              </CardTitle>
              <CardDescription>
                Manage team settings and preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full" variant="outline">
                <Link href={`/dashboard/teams/${teamId}/settings`}>Settings</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Team Activity</CardTitle>
          <CardDescription>
            Latest actions taken by team members
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Video className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No recent activity to display</p>
            <p className="text-sm mt-1">Team activity will appear here once clips are created</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}