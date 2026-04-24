import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { resolveEffectiveMemberId } from "@/lib/resolve-team-member-id";
import { isAdminCached } from "@/lib/admin-helpers";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import { RemotionEditorWrapper } from "./components/RemotionEditorWrapper";
import type { RemotionEditorProps } from "@/types/remotionEditor";

export default async function EditClipPage({
  params,
  searchParams,
}: {
  params: Promise<{ clipId: string }>;
  searchParams: Promise<{ teamId?: string }>;
}) {
  const { clipId } = await params;
  const { teamId } = await searchParams;

  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    throw new Error("User not authenticated");
  }

  // Resolve effective member_id and admin status
  const [effectiveMemberId, isAdmin] = await Promise.all([
    resolveEffectiveMemberId(user.id, teamId, supabaseAdminClient),
    isAdminCached(user.id, supabaseAdminClient),
  ]);

  if (!effectiveMemberId && !isAdmin) {
    throw new Error("User setup incomplete");
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

  let clipQuery = supabase
    .from("parliament_member_clips")
    .select(
      `
    *,
    parliament_members!parliament_member_clips_member_id_fkey (
      member_id,
      display_name,
      full_title,
      given_name,
      family_name,
      party_name,
      party_abbreviation,
      party_background_colour,
      party_foreground_colour,
      constituency_name,
      house_name,
      gender,
      is_current_member
    )
  `
    )
    .eq("id", clipId)
    .eq("is_deleted", false);

  let isLD = false;
  let ldMemberIds: number[] = [];

  if (!isAdmin) {
    isLD = await isLiberalDemocratCached(
      user.id,
      teamId,
      supabaseAdminClient
    );
    if (isLD) {
      ldMemberIds = await getLDMemberIds(supabaseAdminClient);
      clipQuery = clipQuery.in("member_id", ldMemberIds);
    } else {
      clipQuery = clipQuery.eq("member_id", effectiveMemberId!);
    }
  }

  const { data: mainClip, error: clipError } = await clipQuery.single();

  if (clipError) {
    throw new Error("Clip not found or access denied");
  }

  if (!mainClip) {
    throw new Error("Clip not found");
  }

  const sessionuid = mainClip.session_uid;
  const mpId = mainClip.member_id;

  if (!sessionuid) {
    throw new Error("Session UID not found");
  }

  const { data: parliamentEvent, error: eventError } = await supabase
    .from("parliament_events")
    .select("session_length_seconds, session_date, title")
    .eq("event_id", sessionuid)
    .eq("is_deleted", false)
    .single();

  if (eventError && eventError.code !== "PGRST116") {
    console.warn(
      "Error fetching parliament event session length:",
      eventError.message
    );
  }

  const sessionLengthSeconds = parliamentEvent?.session_length_seconds ?? null;
  const sessionDate =
    parliamentEvent?.session_date ?? mainClip.session_date ?? "";
  const eventTitle = parliamentEvent?.title ?? null;

  // Session clips query: filter to LD members for LD users to prevent
  // leaking non-LD clips from the same session
  let sessionClipsQuery = supabase
    .from("parliament_member_clips")
    .select(
      `
    id,
    member_id,
    thumbnail_url,
    vertical_thumbnail_url,
    start_timestamp,
    end_timestamp,
    transcript,
    description,
    session_uid,
    parliament_members!parliament_member_clips_member_id_fkey (
      display_name
    )
  `
    )
    .eq("session_uid", sessionuid)
    .eq("is_deleted", false);

  if (isLD && !isAdmin) {
    sessionClipsQuery = sessionClipsQuery.in("member_id", ldMemberIds);
  }

  const { data: sessionClips, error: sessionClipError } =
    await sessionClipsQuery;

  if (sessionClipError) {
    throw new Error(
      "Error getting session clips: " + sessionClipError.message
    );
  }

  const editorProps: RemotionEditorProps = {
    mpName: mainClip.parliament_members.display_name ?? "Unknown MP",
    sessionDate,
    eventTitle,
    sessionClips: sessionClips || [],
    mainMpId: mpId,
    activeClipId: clipId,
    fullVideoUrl: mainClip.full_video_path,
    sessionLengthSeconds,
    mainClip: {
      id: mainClip.id,
      member_id: mainClip.member_id,
      session_uid: mainClip.session_uid,
      full_video_path: mainClip.full_video_path,
      thumbnail_url: mainClip.thumbnail_url,
      vertical_thumbnail_url: mainClip.vertical_thumbnail_url,
      start_timestamp: mainClip.start_timestamp,
      end_timestamp: mainClip.end_timestamp,
      transcript: mainClip.transcript,
      description: mainClip.description,
      parliament_members: {
        member_id: mainClip.parliament_members.member_id,
        display_name: mainClip.parliament_members.display_name,
        party_name: mainClip.parliament_members.party_name,
        party_abbreviation: mainClip.parliament_members.party_abbreviation,
        party_background_colour:
          mainClip.parliament_members.party_background_colour,
        party_foreground_colour:
          mainClip.parliament_members.party_foreground_colour,
      },
    },
    teamId,
    userId: user.id,
  };

  return <RemotionEditorWrapper {...editorProps} />;
}
