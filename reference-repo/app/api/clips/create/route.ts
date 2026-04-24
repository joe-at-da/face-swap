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

interface Segment {
  start_timestamp: string;
  end_timestamp: string;
}

interface CreateClipRequest {
  clipId: string;
  segments: Segment[];
  watermark_url?: string | null;
  watermark_position?: "center" | "top_left" | "top_right" | "bottom_left" | "bottom_right";
  teamId?: string;
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
    let body: CreateClipRequest;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { clipId, segments, watermark_url, watermark_position, teamId } = body;

    // Validate request
    if (!clipId || typeof clipId !== "string") {
      return NextResponse.json(
        { error: "clipId is required" },
        { status: 400 }
      );
    }

    if (!segments || !Array.isArray(segments) || segments.length === 0) {
      return NextResponse.json(
        { error: "At least one segment is required" },
        { status: 400 }
      );
    }

    // Validate UUID format
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
      // Validate teamId format
      if (!uuidRegex.test(teamId)) {
        return NextResponse.json(
          { error: "Invalid teamId format" },
          { status: 400 }
        );
      }

      // Verify user is a team member
      const { data: isMember, error: memberError } = await supabaseAdminClient
        .rpc("is_team_member", {
          p_team_id: teamId,
          p_user_id: user.id,
        });

      if (memberError || !isMember) {
        return NextResponse.json(
          { error: "You are not a member of this team" },
          { status: 403 }
        );
      }

      // Verify team exists and is not deleted
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

    // Verify the source clip exists
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

    // Validate segments
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];

      if (!segment.start_timestamp || !segment.end_timestamp) {
        return NextResponse.json(
          {
            error: `Segment ${
              i + 1
            }: start_timestamp and end_timestamp are required`,
          },
          { status: 400 }
        );
      }


      // Validate timestamp format (HH:MM:SS)
      const timestampRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$/;
      if (
        !timestampRegex.test(segment.start_timestamp) ||
        !timestampRegex.test(segment.end_timestamp)
      ) {
        return NextResponse.json(
          {
            error: `Segment ${i + 1}: invalid timestamp format (use HH:MM:SS)`,
          },
          { status: 400 }
        );
      }

      // Validate that start is before end
      const startSeconds = parseTimestamp(segment.start_timestamp);
      const endSeconds = parseTimestamp(segment.end_timestamp);

      if (startSeconds >= endSeconds) {
        return NextResponse.json(
          {
            error: `Segment ${i + 1}: start time must be before end time`,
          },
          { status: 400 }
        );
      }

      // Validate segment duration (min 1 second, no maximum limit)
      const duration = endSeconds - startSeconds;
      if (duration < 1) {
        return NextResponse.json(
          {
            error: `Segment ${i + 1}: minimum duration is 1 second`,
          },
          { status: 400 }
        );
      }
    }

    // Validate global watermark position if provided
    if (watermark_position && ![
      "center",
      "top_left", 
      "top_right",
      "bottom_left",
      "bottom_right",
    ].includes(watermark_position)) {
      return NextResponse.json(
        { error: "Invalid watermark_position" },
        { status: 400 }
      );
    }

    // Convert segments to database format (MM:SS.mmm) - no watermark fields per segment
    const dbSegments = segments.map(segment => ({
      start_timestamp: convertToDbTimestampFormat(segment.start_timestamp),
      end_timestamp: convertToDbTimestampFormat(segment.end_timestamp)
    }));

    // Calculate total duration from all segments
    const totalDurationSeconds = segments.reduce((total, segment) => {
      const startSeconds = parseTimestamp(segment.start_timestamp);
      const endSeconds = parseTimestamp(segment.end_timestamp);
      return total + (endSeconds - startSeconds);
    }, 0);

    // Convert total duration to MM:SS.000 format for database
    const totalDurationFormatted = formatDurationForDatabase(totalDurationSeconds);

    // Create user clip record
    const { data: userClip, error: userClipError } = await supabase
      .from("user_clips")
      .insert({
        user_id: user.id,
        team_id: teamId || null,
        clip_id: clipId,
        full_video_path: sourceClip.full_video_path,
        session_uid: sourceClip.session_uid,
        segments: dbSegments,
        duration: totalDurationFormatted,
        watermark_url: watermark_url || null,
        watermark_position: watermark_position || "bottom_right",
        status: "pending_review", // This will trigger the RunPod processing
      })
      .select("id")
      .single();

    if (userClipError) {
      console.error("Failed to create user clip:", userClipError);
      return NextResponse.json(
        { error: "Failed to create clip" },
        { status: 500 }
      );
    }

    // Track video_created event in PostHog
    try {
      const mpContext = await getMPTrackingContext(user.id, teamId);

      await captureServerEvent(user.id, "video_created", {
        // Clip details
        user_clip_id: userClip.id,
        source_clip_id: clipId,
        segment_count: segments.length,
        total_duration_seconds: totalDurationSeconds,
        has_watermark: !!watermark_url,
        watermark_position: watermark_position || "bottom_right",
        session_uid: sourceClip.session_uid,
        // MP Context
        ...mpContext,
      });
    } catch (error) {
      // Log but don't fail the request - analytics should never break core functionality
      console.error("PostHog video_created event capture failed:", error);
    }

    console.log(
      `[Clips API] Created user clip ${userClip.id} from source clip ${clipId} with ${segments.length} segments`
    );

    return NextResponse.json({
      success: true,
      userClipId: userClip.id,
      message: "Clip creation started successfully",
      segments: segments.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Create clip error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Create clip failed: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// Helper function to parse timestamp string to seconds
function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(":");
  const hours = parseInt(parts[0], 10) || 0;
  const minutes = parseInt(parts[1], 10) || 0;
  const seconds = parseInt(parts[2], 10) || 0;

  return hours * 3600 + minutes * 60 + seconds;
}

// Helper function to convert HH:MM:SS to MM:SS.000 format for database
function convertToDbTimestampFormat(timestamp: string): string {
  const totalSeconds = parseTimestamp(timestamp);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  // Format as MM:SS.000 (no milliseconds, so .000)
  return `${minutes.toString().padStart(2, '0')}:${Math.floor(seconds).toString().padStart(2, '0')}.000`;
}

// Helper function to format duration in seconds to MM:SS.000 format for database
function formatDurationForDatabase(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  // Format as MM:SS.000 (no milliseconds, so .000)
  return `${minutes.toString().padStart(2, '0')}:${Math.floor(seconds).toString().padStart(2, '0')}.000`;
}

// GET endpoint for health check
export async function GET() {
  return NextResponse.json({
    success: true,
    message: "Clips Create API is running",
    endpoint: "/api/clips/create",
    method: "POST",
    auth: "Required (authenticated user)",
    timestamp: new Date().toISOString(),
  });
}
