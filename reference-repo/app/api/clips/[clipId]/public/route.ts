import { NextRequest, NextResponse } from "next/server";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

interface RouteParams {
  params: Promise<{ clipId: string }>;
}

/**
 * Public API endpoint to fetch clip data without authentication
 * Used for public clip viewing and embedding
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { clipId } = await params;

    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(clipId)) {
      return NextResponse.json(
        { error: "Invalid clip ID format" },
        { status: 400 }
      );
    }

    // Fetch user clip WITHOUT user_id filter (public access)
    const { data: userClip, error: userClipError } = await supabaseAdminClient
      .from("user_clips")
      .select("*")
      .eq("id", clipId)
      .eq("is_deleted", false)
      .single();

    if (userClipError || !userClip) {
      console.error("Public clip error:", userClipError);
      return NextResponse.json(
        { error: "Clip not found or has been removed" },
        { status: 404 }
      );
    }

    // Fetch parliament member clip details
    const { data: parliamentClip, error: parliamentClipError } = await supabaseAdminClient
      .from("parliament_member_clips")
      .select(`
        id,
        member_id,
        session_type,
        session_date,
        full_video_path
      `)
      .eq("id", userClip.clip_id)
      .single();

    if (parliamentClipError || !parliamentClip) {
      console.error("Parliament clip error:", parliamentClipError);
      return NextResponse.json(
        { error: "Clip details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member details with party colors
    const { data: parliamentMember, error: parliamentMemberError } = await supabaseAdminClient
      .from("parliament_members")
      .select(`
        member_id,
        display_name,
        full_title,
        party_name,
        party_abbreviation,
        party_background_colour,
        party_foreground_colour,
        constituency_name
      `)
      .eq("member_id", parliamentClip.member_id)
      .single();

    if (parliamentMemberError || !parliamentMember) {
      console.error("Parliament member error:", parliamentMemberError);
      return NextResponse.json(
        { error: "Member details not found" },
        { status: 404 }
      );
    }

    // Fetch parliament member portrait
    const { data: portrait } = await supabaseAdminClient
      .from("parliament_member_portraits")
      .select("image_url")
      .eq("member_id", parliamentClip.member_id)
      .eq("is_deleted", false)
      .eq("is_primary", true)
      .single();

    // Add portrait URL to member data if available
    const memberWithPortrait = {
      ...parliamentMember,
      profile_image: portrait?.image_url || null
    };

    // Combine the data for public consumption
    const publicClipData = {
      id: userClip.id,
      created_at: userClip.created_at,
      status: userClip.status,
      duration: userClip.duration,
      segments: userClip.segments,
      transcript: userClip.transcript,
      clip_url: userClip.clip_url,
      vertical_clip_url: userClip.vertical_clip_url,
      thumbnail_url: userClip.thumbnail_url,
      vertical_thumbnail_url: userClip.vertical_thumbnail_url,
      watermark_url: userClip.watermark_url,
      watermark_position: userClip.watermark_position,
      parliament_member_clips: {
        id: parliamentClip.id,
        session_type: parliamentClip.session_type,
        session_date: parliamentClip.session_date,
        parliament_members: memberWithPortrait
      }
    };

    return NextResponse.json({
      success: true,
      data: publicClipData,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Public clip API error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch clip: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
