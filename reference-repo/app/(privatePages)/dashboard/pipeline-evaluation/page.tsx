import { createSupabaseServerClient } from "@/supabase/supabaseServerClient";
import { supabaseAdminClient } from "@/supabase/supabaseAdmin";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import { PipelineEvaluationClient } from "./components/pipeline-evaluation-client";
import {
  EVALUATION_PROCESSING_RUN_IDS,
  type EvaluationStats,
} from "./constants";

// Force dynamic rendering to prevent caching
export const dynamic = "force-dynamic";
export const revalidate = 0;

async function getInitialStats(): Promise<EvaluationStats> {
  // Default stats if no processing runs configured
  if (EVALUATION_PROCESSING_RUN_IDS.length === 0) {
    return {
      totalSegments: 0,
      evaluatedCount: 0,
      correctCount: 0,
      wrongSpeakerCount: 0,
      wrongMpCount: 0,
      remainingCount: 0,
      accuracyPercentage: 0,
    };
  }

  try {
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
      throw totalError;
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
        .not("is_correct", "is", null)
        .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1);

      if (evalError) {
        console.error("Error fetching evaluations:", evalError);
        throw evalError;
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

    return {
      totalSegments: totalSegments ?? 0,
      evaluatedCount,
      correctCount,
      wrongSpeakerCount,
      wrongMpCount,
      remainingCount,
      accuracyPercentage,
    };
  } catch (error) {
    console.error("Error fetching initial stats:", error);
    return {
      totalSegments: 0,
      evaluatedCount: 0,
      correctCount: 0,
      wrongSpeakerCount: 0,
      wrongMpCount: 0,
      remainingCount: 0,
      accuracyPercentage: 0,
    };
  }
}

export default async function PipelineEvaluationPage() {
  const supabase = await createSupabaseServerClient();

  // Get authenticated user
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/");
  }

  // Check if user has @veedoo.io or @veedoo.com email
  const email = user.email;
  if (
    !email ||
    (!email.endsWith("@veedoo.io") && !email.endsWith("@veedoo.com"))
  ) {
    redirect("/dashboard");
  }

  // Fetch initial stats
  const initialStats = await getInitialStats();

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-4xl font-serif font-bold text-foreground tracking-tight">
              Pipeline Evaluation
            </h1>
            <p className="text-xl text-foreground/80 font-medium leading-relaxed">
              Evaluate auto-detected MP identifications from video segments.
            </p>
          </div>
          <Link href="/dashboard/pipeline-evaluation-results">
            <Button variant="outline" size="lg">
              <FileText className="h-4 w-4 mr-2" />
              View Results
            </Button>
          </Link>
        </div>
        {EVALUATION_PROCESSING_RUN_IDS.length === 0 && (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              No processing runs configured for evaluation. Add processing run
              IDs to the constants file to begin.
            </p>
          </div>
        )}
      </div>

      <PipelineEvaluationClient initialStats={initialStats} userId={user.id} />
    </div>
  );
}
