import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { EVALUATION_PROCESSING_RUN_IDS } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";
import type { EvaluationStats } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

export async function GET() {
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

    // Check if we have processing run IDs configured
    if (EVALUATION_PROCESSING_RUN_IDS.length === 0) {
      const emptyStats: EvaluationStats = {
        totalSegments: 0,
        evaluatedCount: 0,
        correctCount: 0,
        wrongSpeakerCount: 0,
        wrongMpCount: 0,
        remainingCount: 0,
        accuracyPercentage: 0,
      };
      return NextResponse.json({ success: true, stats: emptyStats });
    }

    // Count total evaluable segments
    const { count: totalSegments, error: totalError } =
      await supabaseAdminClient
        .from("event_processing_segments")
        .select("id", { count: "exact", head: true })
        .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
        .not("member_id", "is", null)
        .is("manually_assigned_member_id", null)
        .gt("duration_seconds", 5);

    if (totalError) {
      console.error("Error counting total segments:", totalError);
      return NextResponse.json(
        { error: "Failed to count segments" },
        { status: 500 }
      );
    }

    // Get evaluation counts with pagination to handle >1000 rows
    const PAGE_SIZE = 1000;
    let allEvaluations: Array<{
      is_correct: boolean;
      error_reason: string | null;
    }> = [];
    let page = 0;
    let hasMore = true;

    while (hasMore) {
      const { data: evaluations, error: evalError } = await supabaseAdminClient
        .from("segment_evaluations")
        .select("is_correct, error_reason")
        .in("processing_run_id", EVALUATION_PROCESSING_RUN_IDS)
        .not("is_correct", "is", null) // Only count completed evaluations
        .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1);

      if (evalError) {
        console.error("Error fetching evaluations:", evalError);
        return NextResponse.json(
          { error: "Failed to fetch evaluations" },
          { status: 500 }
        );
      }

      if (evaluations && evaluations.length > 0) {
        // Filter out null is_correct values and map to expected type
        // Query already filters with .not("is_correct", "is", null), but TypeScript doesn't know
        const validEvaluations: Array<{
          is_correct: boolean;
          error_reason: string | null;
        }> = evaluations
          .filter((e) => e.is_correct !== null)
          .map((e) => ({
            is_correct: e.is_correct as boolean,
            error_reason: e.error_reason as string | null,
          }));
        allEvaluations = allEvaluations.concat(validEvaluations);
        hasMore = evaluations.length === PAGE_SIZE;
        page++;
      } else {
        hasMore = false;
      }
    }

    const evaluatedCount = allEvaluations.length;
    const correctCount = allEvaluations.filter((e) => e.is_correct).length;
    const wrongSpeakerCount = allEvaluations.filter(
      (e) => e.error_reason === "wrong_speaker_detected"
    ).length;
    const wrongMpCount = allEvaluations.filter(
      (e) => e.error_reason === "wrong_mp_matched"
    ).length;
    const remainingCount = (totalSegments ?? 0) - evaluatedCount;
    const accuracyPercentage =
      evaluatedCount > 0
        ? Math.round((correctCount / evaluatedCount) * 10000) / 100
        : 0;

    const stats: EvaluationStats = {
      totalSegments: totalSegments ?? 0,
      evaluatedCount,
      correctCount,
      wrongSpeakerCount,
      wrongMpCount,
      remainingCount,
      accuracyPercentage,
    };

    return NextResponse.json({ success: true, stats });
  } catch (error) {
    console.error("Stats error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      {
        success: false,
        error: `Failed to fetch stats: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}
