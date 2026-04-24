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

interface CreateClipV2Request {
  clipId: string;
  compositionJson: Record<string, unknown>;
  teamId?: string;
}

const MAX_COMPOSITION_SIZE = 5 * 1024 * 1024; // 5MB limit

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
    let body: CreateClipV2Request;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { clipId, compositionJson, teamId } = body;

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

    // Validate compositionJson
    if (!compositionJson || typeof compositionJson !== "object") {
      return NextResponse.json(
        { error: "compositionJson is required" },
        { status: 400 }
      );
    }

    // Size check
    const jsonStr = JSON.stringify(compositionJson);
    if (jsonStr.length > MAX_COMPOSITION_SIZE) {
      return NextResponse.json(
        { error: "Composition JSON exceeds maximum size" },
        { status: 400 }
      );
    }

    // Zod schema validation
    const parseResult = videoCompositionSchema.safeParse(compositionJson);
    if (!parseResult.success) {
      console.error(
        "Composition validation failed:",
        JSON.stringify(parseResult.error.issues, null, 2)
      );
      return NextResponse.json(
        {
          error: "Invalid composition JSON structure",
          details: parseResult.error.issues,
        },
        { status: 400 }
      );
    }
    const comp = parseResult.data;

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
    const isLD = !isAdmin
      ? await isLiberalDemocratCached(user.id, teamId, supabaseAdminClient)
      : false;
    const ldMemberIds = isLD ? await getLDMemberIds(supabaseAdminClient) : [];

    // Verify the source clip exists (admins can access any clip)
    let sourceClipQuery = supabase
      .from("parliament_member_clips")
      .select("id, member_id, full_video_path, session_uid")
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

    // Extract duration from composition
    const totalDurationSeconds = comp.durationInFrames / comp.fps;
    const minutes = Math.floor(totalDurationSeconds / 60);
    const seconds = Math.floor(totalDurationSeconds % 60);
    const durationFormatted = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.000`;

    // Count image items for tracking
    const imageCount = comp.tracks
      .flatMap((t) => t.items)
      .filter((i) => i.type === "image").length;

    // Create user clip record with composition JSON
    // NOTE: composition_json and editor_version columns are added by migration
    // 20260206193240_add_composition_json_to_user_clips.sql
    // After applying migration, run `pnpm genTypes` to update types.
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
      composition_json: compositionJson,
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
      console.error("Failed to create user clip (v2):", userClipError);
      return NextResponse.json(
        { error: "Failed to create clip" },
        { status: 500 }
      );
    }

    // Track video_created event in PostHog
    try {
      const mpContext = await getMPTrackingContext(user.id, teamId);

      await captureServerEvent(user.id, "video_created", {
        user_clip_id: userClip.id,
        source_clip_id: clipId,
        editor_version: 2,
        total_duration_seconds: totalDurationSeconds,
        image_count: imageCount,
        canvas_mode: comp.width === 1920 ? "landscape" : "vertical",
        track_count: comp.tracks.length,
        session_uid: sourceClip.session_uid,
        ...mpContext,
      });
    } catch (error) {
      console.error("PostHog video_created event capture failed:", error);
    }

    return NextResponse.json({
      success: true,
      userClipId: userClip.id,
      message: "Clip export started successfully",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    ErrorLogger.logError(error, {
      component: "clips/create-v2",
      action: "export",
      feature: "remotion-editor",
    });

    return NextResponse.json(
      {
        success: false,
        error: "An internal error occurred while creating the clip",
      },
      { status: 500 }
    );
  }
}
