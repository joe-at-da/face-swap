import { Suspense } from "react";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { redirect, notFound } from "next/navigation";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { resolveEffectiveMemberId } from "@/lib/resolve-team-member-id";
import { isAdminCached } from "@/lib/admin-helpers";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import ClipDetailView from "./components/clip-detail-view";

interface PageProps {
  params: Promise<{ clipId: string }>;
  searchParams: Promise<{ teamId?: string }>;
}

async function getClipData(clipId: string, teamId?: string) {
  const supabase = await createSupabaseServerClient();

  // Get authenticated user
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();
  if (authError || !user) {
    redirect("/auth/login");
  }

  const isAdmin = await isAdminCached(user.id, supabaseAdminClient);

  // Non-admins must have an effective member to view clips
  let effectiveMemberId: number | null = null;
  if (!isAdmin) {
    effectiveMemberId = await resolveEffectiveMemberId(user.id, teamId, supabaseAdminClient);
    if (!effectiveMemberId) {
      redirect("/setup");
    }
  }

  // IDOR protection: verify team membership when teamId is provided
  if (teamId) {
    const { data: isMember, error: memberError } =
      await supabaseAdminClient.rpc("is_team_member", {
        p_team_id: teamId,
        p_user_id: user.id,
      });

    if (memberError || !isMember) {
      redirect("/dashboard");
    }
  }

  // Build clip query — admins see any clip, LD users see LD clips,
  // non-LD non-admin users restricted to their member
  let clipQuery = supabase
    .from("parliament_member_clips")
    .select("*")
    .eq("id", clipId)
    .eq("is_deleted", false);

  if (!isAdmin) {
    const isLD = await isLiberalDemocratCached(
      user.id,
      teamId,
      supabaseAdminClient
    );
    if (isLD) {
      const ldMemberIds = await getLDMemberIds(supabaseAdminClient);
      clipQuery = clipQuery.in("member_id", ldMemberIds);
    } else {
      clipQuery = clipQuery.eq("member_id", effectiveMemberId!);
    }
  }

  const { data: clip, error: clipError } = await clipQuery.single();

  if (clipError || !clip) {
    notFound();
  }

  // Fetch MP data using the clip's member_id (valid for both admin and non-admin)
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
    .eq("member_id", clip.member_id)
    .eq("is_deleted", false)
    .single();

  if (mpError || !mp) {
    throw new Error("Failed to fetch MP data");
  }

  // Fetch parliament event data if session_uid exists
  let parliamentEvent = null;
  if (clip && clip.session_uid) {
    const { data: eventData, error: eventError } = await supabaseAdminClient
      .from("parliament_events")
      .select("title, session_date")
      .eq("event_id", clip.session_uid)
      .eq("is_deleted", false)
      .single();

    if (!eventError && eventData) {
      parliamentEvent = eventData;
    }
  }

  return {
    clip,
    mp,
    teamId,
    parliamentEvent,
  };
}

export async function generateMetadata({ params, searchParams }: PageProps) {
  try {
    const { clipId } = await params;
    const searchParamsData = await searchParams;
    const { clip, mp } = await getClipData(clipId, searchParamsData.teamId);
    const title = `Clip from ${mp.display_name}`;

    return {
      title: `${title} - Parliament Connect`,
      description: clip.transcript.substring(0, 150) + "...",
    };
  } catch {
    return {
      title: "Clip Not Found - Parliament Connect",
      description: "The requested clip could not be found.",
    };
  }
}

export default async function ClipDetailPage({
  params,
  searchParams,
}: PageProps) {
  const { clipId } = await params;
  const searchParamsData = await searchParams;
  const teamId = searchParamsData.teamId;

  const { clip, mp, parliamentEvent } = await getClipData(clipId, teamId);

  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ClipDetailView
        clip={clip}
        mp={mp}
        teamId={teamId}
        parliamentEvent={parliamentEvent}
      />
    </Suspense>
  );
}
