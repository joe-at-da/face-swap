import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";

export type SkipReason =
  | "bad_quality"
  | "no_speaker_faces"
  | "already_added_similar_pictures";

interface SkipSegmentRequest {
  segmentId: string;
  skipReason: SkipReason;
}

export async function POST(request: Request) {
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

    // Check if user has @veedoo.io or @veedoo.com email
    const email = user.email;
    if (
      !email ||
      (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
    ) {
      return NextResponse.json(
        { error: "Forbidden: Access restricted to Veedoo team members" },
        { status: 403 }
      );
    }

    // Parse request body
    const body = (await request.json()) as SkipSegmentRequest;
    const { segmentId, skipReason } = body;

    if (!segmentId || !skipReason) {
      return NextResponse.json(
        { error: "Missing required fields: segmentId and skipReason" },
        { status: 400 }
      );
    }

    // Validate skip reason
    if (
      skipReason !== "bad_quality" &&
      skipReason !== "no_speaker_faces" &&
      skipReason !== "already_added_similar_pictures"
    ) {
      return NextResponse.json(
        {
          error:
            'Invalid skip reason. Must be "bad_quality", "no_speaker_faces", or "already_added_similar_pictures"',
        },
        { status: 400 }
      );
    }

    // Check if evaluation exists for this segment
    const { data: existingEvaluation, error: fetchError } =
      await supabaseAdminClient
        .from("portrait_collection_evaluations")
        .select("id, locked_by, member_id_selected, skip_reason")
        .eq("segment_id", segmentId)
        .single();

    if (fetchError && fetchError.code !== "PGRST116") {
      // PGRST116 = not found
      console.error("Error fetching evaluation:", fetchError);
      return NextResponse.json(
        { error: "Failed to fetch evaluation" },
        { status: 500 }
      );
    }

    // If evaluation doesn't exist, return error
    if (!existingEvaluation) {
      return NextResponse.json(
        { error: "Segment not found or not locked for evaluation" },
        { status: 404 }
      );
    }

    // Check if the segment is locked by this user
    if (existingEvaluation.locked_by !== user.id) {
      return NextResponse.json(
        { error: "This segment is locked by another user" },
        { status: 409 }
      );
    }

    // Check if already completed or skipped
    if (existingEvaluation.member_id_selected) {
      return NextResponse.json(
        { error: "This segment has already been evaluated" },
        { status: 409 }
      );
    }

    if (existingEvaluation.skip_reason) {
      return NextResponse.json(
        { error: "This segment has already been skipped" },
        { status: 409 }
      );
    }

    // Update evaluation with skip reason and clear lock
    const { error: updateError } = await supabaseAdminClient
      .from("portrait_collection_evaluations")
      .update({
        skip_reason: skipReason,
        evaluated_by: user.id,
        updated_at: new Date().toISOString(),
        locked_by: null,
        locked_at: null,
      })
      .eq("segment_id", segmentId);

    if (updateError) {
      console.error("Error updating evaluation:", updateError);
      return NextResponse.json(
        { error: "Failed to skip segment" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      segmentId,
      skipReason,
    });
  } catch (error) {
    console.error("Skip segment error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to skip segment: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
