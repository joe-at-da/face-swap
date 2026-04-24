import { Suspense } from "react";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect } from "next/navigation";
import ClipsListView from "./components/clips-list-view";
import { Skeleton } from "@/components/ui/skeleton";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { isActualMPCached } from "@/lib/user-helpers";
import { resolveEffectiveMemberId } from "@/lib/resolve-team-member-id";

interface CreateClipsPageProps {
  searchParams: Promise<{
    teamId?: string;
  }>;
}

async function getClipsData(teamId?: string) {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user) {
    redirect("/auth/login");
  }

  const effectiveMemberId = await resolveEffectiveMemberId(user.id, teamId, supabaseAdminClient);

  if (!effectiveMemberId) {
    const isActualMPUser = await isActualMPCached(user.id, user.email!, supabaseAdminClient);

    if (!isActualMPUser) {
      if (teamId) {
        redirect(`/dashboard/teams/${teamId}`);
      }
      redirect("/dashboard");
    }

    redirect("/setup");
  }

  // Validate team membership if teamId is provided
  let team = null;
  if (teamId) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(teamId)) {
      throw new Error("Invalid team ID format");
    }

    const { data: isMember, error: memberError } = await supabaseAdminClient
      .rpc("is_team_member", {
        p_team_id: teamId,
        p_user_id: user.id,
      });

    if (memberError || !isMember) {
      throw new Error("You are not a member of this team");
    }

    const { data: teamData, error: teamError } = await supabase
      .from("teams")
      .select("id, name, description")
      .eq("id", teamId)
      .eq("is_deleted", false)
      .single();

    if (teamError || !teamData) {
      throw new Error("Team not found");
    }

    team = teamData;
  }

  // Get MP details
  const { data: mp, error: mpError } = await supabase
    .from("parliament_members")
    .select(
      `
      display_name,
      party_abbreviation,
      party_name,
      constituency_name,
      parliament_member_portraits(
        image_url,
        is_primary
      )
    `
    )
    .eq("member_id", effectiveMemberId)
    .eq("is_deleted", false)
    .single();

  if (mpError) {
    throw new Error("Failed to fetch MP data");
  }

  return {
    mp,
    memberId: effectiveMemberId,
    team,
    teamId,
  };
}

function ClipsLoadingSkeleton() {
  return (
    <div className="space-y-8">
      {/* Header skeleton */}
      <div className="space-y-4">
        <div>
          <Skeleton className="h-11 w-64" />
          <Skeleton className="h-7 w-96 mt-2" />
        </div>

        {/* MP Info skeleton */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-16 w-16 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-7 w-40" />
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-6 w-12" />
            </div>
          </div>
        </div>
      </div>

      {/* Search and filters skeleton */}
      <div className="space-y-4">
        <div className="border rounded-lg p-6">
          <Skeleton className="h-11 w-full max-w-2xl" />
          <div className="flex gap-2 mt-4">
            <Skeleton className="h-11 w-32" />
            <Skeleton className="h-11 w-40" />
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="flex gap-4">
            <Skeleton className="h-11 w-48" />
            <Skeleton className="h-11 w-28" />
            <Skeleton className="h-11 w-32" />
          </div>
        </div>
      </div>

      {/* Results summary skeleton */}
      <Skeleton className="h-5 w-48" />

      {/* Grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="space-y-4 border rounded-lg overflow-hidden">
            <Skeleton className="aspect-video w-full" />
            <div className="p-4 space-y-3">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <div className="flex justify-between items-center pt-2 border-t">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-5 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function CreateClipsPage({ searchParams }: CreateClipsPageProps) {
  const params = await searchParams;
  const teamId = params.teamId;

  return (
    <div className="space-y-8">
      <Suspense fallback={<ClipsLoadingSkeleton />}>
        <ClipsDataWrapper teamId={teamId} />
      </Suspense>
    </div>
  );
}

async function ClipsDataWrapper({ teamId }: { teamId?: string }) {
  const { mp, memberId, team } = await getClipsData(teamId);

  return <ClipsListView mp={mp} memberId={memberId} team={team} teamId={teamId} />;
}
