import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import type { ErrorReason } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

interface SubmitBody {
  segmentId: string;
  isCorrect: boolean;
  errorReason?: ErrorReason;
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
    let body: SubmitBody;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON in request body" },
        { status: 400 }
      );
    }

    const { segmentId, isCorrect, errorReason } = body;

    // Validate segmentId
    if (!segmentId || typeof segmentId !== "string") {
      return NextResponse.json(
        { error: "segmentId is required and must be a string" },
        { status: 400 }
      );
    }

    // Validate isCorrect
    if (typeof isCorrect !== "boolean") {
      return NextResponse.json(
        { error: "isCorrect is required and must be a boolean" },
        { status: 400 }
      );
    }

    // Validate errorReason when isCorrect is false
    if (!isCorrect) {
      if (!errorReason) {
        return NextResponse.json(
          { error: "errorReason is required when isCorrect is false" },
          { status: 400 }
        );
      }
      if (
        errorReason !== "wrong_speaker_detected" &&
        errorReason !== "wrong_mp_matched"
      ) {
        return NextResponse.json(
          {
            error:
              "errorReason must be 'wrong_speaker_detected' or 'wrong_mp_matched'",
          },
          { status: 400 }
        );
      }
    }

    // Verify the segment exists and get its processing_run_id
    const { data: segment, error: segmentError } = await supabaseAdminClient
      .from("event_processing_segments")
      .select("id, processing_run_id")
      .eq("id", segmentId)
      .single();

    if (segmentError || !segment) {
      console.error("Error fetching segment:", segmentError);
      return NextResponse.json({ error: "Segment not found" }, { status: 404 });
    }

    // Update the evaluation
    const { error: updateError } = await supabaseAdminClient
      .from("segment_evaluations")
      .upsert(
        {
          segment_id: segmentId,
          processing_run_id: segment.processing_run_id,
          evaluated_by: user.id,
          is_correct: isCorrect,
          error_reason: isCorrect ? null : errorReason,
          locked_by: null, // Clear the lock
          locked_at: null,
          updated_at: new Date().toISOString(),
        },
        {
          onConflict: "segment_id",
          ignoreDuplicates: false,
        }
      );

    if (updateError) {
      console.error("Error submitting evaluation:", updateError);
      return NextResponse.json(
        { error: "Failed to submit evaluation" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Evaluation submitted successfully",
    });
  } catch (error) {
    console.error("Submit evaluation error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to submit evaluation: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
