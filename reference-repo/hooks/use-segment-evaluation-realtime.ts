import { useEffect, useRef } from "react";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { RealtimeChannel } from "@supabase/supabase-js";
import { EVALUATION_PROCESSING_RUN_IDS } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

interface EvaluationData {
  id: string;
  segment_id: string;
  is_correct: boolean;
  error_reason: string | null;
  evaluated_by: string;
  processing_run_id: string;
  created_at: string;
}

interface UseSegmentEvaluationRealtimeOptions {
  onEvaluationAdded: (evaluation: EvaluationData) => void;
  enabled?: boolean;
}

/**
 * Hook to subscribe to realtime updates for segment evaluations
 * Allows multiple users to see evaluations as they happen in real-time
 */
export function useSegmentEvaluationRealtime({
  onEvaluationAdded,
  enabled = true,
}: UseSegmentEvaluationRealtimeOptions) {
  const onEvaluationAddedRef = useRef(onEvaluationAdded);

  useEffect(() => {
    onEvaluationAddedRef.current = onEvaluationAdded;
  }, [onEvaluationAdded]);

  useEffect(() => {
    if (!enabled || EVALUATION_PROCESSING_RUN_IDS.length === 0) return;

    const supabase = createSupabaseBrowserClient();
    let channel: RealtimeChannel | null = null;
    let isMounted = true;

    const setupRealtimeSubscription = async () => {
      // Get session for auth
      const {
        data: { session },
        error: authError,
      } = await supabase.auth.getSession();

      if (authError || !session) {
        if (authError) console.error("Failed to get session for realtime:", authError);
        return;
      }

      // Check if component is still mounted before continuing
      if (!isMounted) return;

      // Set auth token for realtime
      await supabase.realtime.setAuth(session.access_token);

      // Check again after async operation
      if (!isMounted) return;

      // Create channel for segment evaluations
      channel = supabase.channel("segment-evaluations");

      // Subscribe to INSERT and UPDATE events on segment_evaluations table
      channel
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "segment_evaluations",
          },
          (payload) => {
            const evaluation = payload.new as EvaluationData;

            // Only process if it's for one of our configured processing runs
            // and it has a completed evaluation (is_correct is not null)
            if (
              evaluation &&
              EVALUATION_PROCESSING_RUN_IDS.includes(evaluation.processing_run_id) &&
              evaluation.is_correct !== null
            ) {
              onEvaluationAddedRef.current(evaluation);
            }
          }
        )
        .on(
          "postgres_changes",
          {
            event: "UPDATE",
            schema: "public",
            table: "segment_evaluations",
          },
          (payload) => {
            const evaluation = payload.new as EvaluationData;
            const oldEvaluation = payload.old as Partial<EvaluationData>;

            // Only process if the evaluation was just completed
            // (is_correct changed from null/undefined to a value)
            // Note: Without REPLICA IDENTITY FULL, oldEvaluation.is_correct will be undefined
            if (
              evaluation &&
              EVALUATION_PROCESSING_RUN_IDS.includes(evaluation.processing_run_id) &&
              evaluation.is_correct !== null &&
              (oldEvaluation.is_correct === null || oldEvaluation.is_correct === undefined)
            ) {
              onEvaluationAddedRef.current(evaluation);
            }
          }
        )
        .subscribe((status) => {
          if (status === "SUBSCRIBED") {
            console.log("Subscribed to segment evaluations realtime");
          } else if (status === "CHANNEL_ERROR") {
            console.error("Realtime channel error");
          }
        });
    };

    setupRealtimeSubscription();

    return () => {
      isMounted = false;
      if (channel) {
        console.log("Unsubscribing from segment evaluations channel");
        supabase.removeChannel(channel);
      }
    };
  }, [enabled]);
}
