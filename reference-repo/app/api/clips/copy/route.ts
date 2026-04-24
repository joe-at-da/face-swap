import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { captureServerEvent } from "@/lib/posthog-server";
import { getMPTrackingContext } from "@/lib/posthog-helpers";
import { resolveEffectiveMemberId } from "@/lib/resolve-team-member-id";
import { isAdminCached } from "@/lib/admin-helpers";
import {
  isLiberalDemocratCached,
  getLDMemberIds,
} from "@/lib/liberal-democrat-helpers";
import { ErrorLogger } from "@/lib/errorLogger";
import { videoCompositionSchema } from "@/schemas/compositionSchema";

interface CopyClipRequest {
  clipId: string;
  teamId?: string;
}

const FPS = 30;

/**
 * Parse timestamp from "MM:SS.mmm" or "HH:MM:SS.mmm" format to milliseconds.
 * Mirrors the client-side parseTimestampToMs in stores/editorStore.ts.
 */
function parseTimestampToMs(timestamp: string): number {
  const [timePart, msPart] = timestamp.split(".");
  const parts = timePart.split(":");

  if (parts.length === 3) {
    const [hours, minutes, seconds] = parts.map(Number);
    return (
      (hours * 3600 + minutes * 60 + seconds) * 1000 +
      (msPart ? Number(msPart.padEnd(3, "0").slice(0, 3)) : 0)
    );
  }
  const [minutes, seconds] = parts.map(Number);
  return (
    (minutes * 60 + seconds) * 1000 +
    (msPart ? Number(msPart.padEnd(3, "0").slice(0, 3)) : 0)
  );
}

export async function POST(request: NextRequest) {
  try {
    const supabase = await createSupabaseServerClient();

    // Get authenticated user
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse request body
    let body: CopyClipRequest;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { clipId, teamId } = body;

    // Validate clipId
    if (!clipId || typeof clipId !== "string") {
      return NextResponse.json(
        { error: "clipId is required" },
        { status: 400 }
      );
    }

    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(clipId)) {
      return NextResponse.json(
        { error: "Invalid clipId format" },
        { status: 400 }
      );
    }

    // Validate and verify team membership if teamId is provided
    if (teamId) {
      if (!uuidRegex.test(teamId)) {
        return NextResponse.json(
          { error: "Invalid teamId format" },
          { status: 400 }
        );
      }

      const { data: isMember, error: memberError } =
        await supabaseAdminClient.rpc("is_team_member", {
          p_team_id: teamId,
          p_user_id: user.id,
        });

      if (memberError || !isMember) {
        return NextResponse.json(
          { error: "You are not a member of this team" },
          { status: 403 }
        );
      }

      const { data: team, error: teamError } = await supabase
        .from("teams")
        .select("id")
        .eq("id", teamId)
        .eq("is_deleted", false)
        .single();

      if (teamError || !team) {
        return NextResponse.json(
          { error: "Team not found" },
          { status: 404 }
        );
      }
    }

    // Resolve effective member_id and admin status
    const [effectiveMemberId, isAdmin] = await Promise.all([
      resolveEffectiveMemberId(user.id, teamId, supabaseAdminClient),
      isAdminCached(user.id, supabaseAdminClient),
    ]);

    if (!effectiveMemberId && !isAdmin) {
      return NextResponse.json(
        { error: "User setup incomplete" },
        { status: 400 }
      );
    }

    // Check LD status for cross-party clip access
    const isLD = await isLiberalDemocratCached(
      user.id,
      teamId,
      supabaseAdminClient
    );
    const ldMemberIds = isLD ? await getLDMemberIds(supabaseAdminClient) : [];

    // Fetch source clip with all fields needed for composition
    let sourceClipQuery = supabase
      .from("parliament_member_clips")
      .select(
        "id, member_id, full_video_path, session_uid, start_timestamp, end_timestamp, duration_seconds"
      )
      .eq("id", clipId)
      .eq("is_deleted", false);

    if (!isAdmin) {
      if (isLD) {
        sourceClipQuery = sourceClipQuery.in("member_id", ldMemberIds);
      } else {
        sourceClipQuery = sourceClipQuery.eq("member_id", effectiveMemberId!);
      }
    }

    const { data: sourceClip, error: sourceClipError } =
      await sourceClipQuery.single();

    if (sourceClipError || !sourceClip) {
      return NextResponse.json(
        { error: "Source clip not found or access denied" },
        { status: 404 }
      );
    }

    // Parse timestamps and calculate frame values
    const startMs = parseTimestampToMs(sourceClip.start_timestamp);
    const endMs = parseTimestampToMs(sourceClip.end_timestamp);
    const durationSeconds = sourceClip.duration_seconds ?? (endMs - startMs) / 1000;
    const durationInFrames = Math.round(durationSeconds * FPS);
    const startFrom = Math.round((startMs / 1000) * FPS);
    const endAt = Math.round((endMs / 1000) * FPS);

    // Build v2 composition JSON
    const composition = {
      version: 2 as const,
      fps: 30 as const,
      width: 1920,
      height: 1080,
      durationInFrames,
      tracks: [
        {
          id: "track-video-0",
          name: "Video 1",
          type: "video" as const,
          items: [
            {
              id: "item-0",
              type: "video" as const,
              from: 0,
              durationInFrames,
              src: sourceClip.full_video_path,
              startFrom,
              endAt,
              playbackRate: 1,
              volume: 1,
              isMuted: false,
            },
          ],
          transitions: [],
        },
      ],
      subtitles: null,
      metadata: {
        clipId,
        userId: user.id,
        teamId: teamId ?? null,
        createdAt: new Date().toISOString(),
        outputFormat: "landscape" as const,
      },
    };

    // Validate composition against schema
    const parseResult = videoCompositionSchema.safeParse(composition);
    if (!parseResult.success) {
      console.error(
        "Copy composition validation failed:",
        JSON.stringify(parseResult.error.issues, null, 2)
      );
      return NextResponse.json(
        { error: "Failed to build valid composition" },
        { status: 500 }
      );
    }

    // Format duration for database (MM:SS.000)
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = Math.floor(durationSeconds % 60);
    const durationFormatted = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.000`;

    // Insert into user_clips with v2 format
    const insertData = {
      user_id: user.id,
      team_id: teamId || null,
      clip_id: clipId,
      full_video_path: sourceClip.full_video_path,
      session_uid: sourceClip.session_uid,
      segments: [] as unknown[],
      duration: durationFormatted,
      watermark_url: null,
      watermark_position: "bottom_right" as const,
      composition_json: composition,
      editor_version: 2,
      status: "pending_review" as const,
    };

    const { data: userClip, error: userClipError } = await supabase
      .from("user_clips")
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .insert(insertData as any)
      .select("id")
      .single();

    if (userClipError) {
      console.error("Failed to copy clip:", userClipError);
      return NextResponse.json(
        { error: "Failed to copy clip" },
        { status: 500 }
      );
    }

    // Track video_copied event in PostHog
    try {
      const mpContext = await getMPTrackingContext(user.id, teamId);

      await captureServerEvent(user.id, "video_copied", {
        user_clip_id: userClip.id,
        source_clip_id: clipId,
        editor_version: 2,
        total_duration_seconds: durationSeconds,
        session_uid: sourceClip.session_uid,
        ...mpContext,
      });
    } catch (error) {
      console.error("PostHog video_copied event capture failed:", error);
    }

    console.log(
      `[Clips Copy API] Copied parliament clip ${clipId} → user clip ${userClip.id} (v2 composition)`
    );

    return NextResponse.json({
      success: true,
      userClipId: userClip.id,
      message: "Clip copy started successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    ErrorLogger.logError(error, {
      component: "clips/copy",
      action: "copy-clip",
      feature: "clips",
    });

    return NextResponse.json(
      {
        success: false,
        error: "An internal error occurred while copying the clip",
      },
      { status: 500 }
    );
  }
}
