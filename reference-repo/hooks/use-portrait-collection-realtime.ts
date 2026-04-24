import { useEffect, useRef } from "react";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { RealtimeChannel } from "@supabase/supabase-js";
import { EVALUATION_PROCESSING_RUN_IDS } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface PortraitCollectionData {
  id: string;
  segment_id: string;
  member_id_selected: number;
  evaluated_by: string;
  processing_run_id: string;
  selected_face_indices: number[];
  rejected_face_indices: number[];
  portraits_added: string[];
  created_at: string;
}

interface UsePortraitCollectionRealtimeOptions {
  onEvaluationAdded: (evaluation: PortraitCollectionData) => void;
  enabled?: boolean;
}

/**
 * Hook to subscribe to realtime updates for portrait collection evaluations
 * Allows multiple users to see identifications as they happen in real-time
 */
export function usePortraitCollectionRealtime({
  onEvaluationAdded,
  enabled = true,
}: UsePortraitCollectionRealtimeOptions) {
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
        if (authError)
          console.error("Failed to get session for realtime:", authError);
        return;
      }

      // Check if component is still mounted before continuing
      if (!isMounted) return;

      // Set auth token for realtime
      await supabase.realtime.setAuth(session.access_token);

      // Check again after async operation
      if (!isMounted) return;

      // Create channel for portrait collection evaluations
      channel = supabase.channel("portrait-collection-evaluations");

      // Subscribe to INSERT and UPDATE events on portrait_collection_evaluations table
      channel
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "portrait_collection_evaluations",
          },
          (payload) => {
            const evaluation = payload.new as PortraitCollectionData;

            // Only process if it's for one of our configured processing runs
            // and it has a completed evaluation (member_id_selected is not null)
            if (
              evaluation &&
              EVALUATION_PROCESSING_RUN_IDS.includes(
                evaluation.processing_run_id
              ) &&
              evaluation.member_id_selected !== null
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
            table: "portrait_collection_evaluations",
          },
          (payload) => {
            const evaluation = payload.new as PortraitCollectionData;
            const oldEvaluation =
              payload.old as Partial<PortraitCollectionData>;

            // Only process if the evaluation was just completed
            // (member_id_selected changed from null/undefined to a value)
            if (
              evaluation &&
              EVALUATION_PROCESSING_RUN_IDS.includes(
                evaluation.processing_run_id
              ) &&
              evaluation.member_id_selected !== null &&
              (oldEvaluation.member_id_selected === null ||
                oldEvaluation.member_id_selected === undefined)
            ) {
              onEvaluationAddedRef.current(evaluation);
            }
          }
        )
        .subscribe((status) => {
          if (status === "SUBSCRIBED") {
            console.log("Subscribed to portrait collection evaluations realtime");
          } else if (status === "CHANNEL_ERROR") {
            console.error("Realtime channel error");
          }
        });
    };

    setupRealtimeSubscription();

    return () => {
      isMounted = false;
      if (channel) {
        console.log("Unsubscribing from portrait collection evaluations channel");
        supabase.removeChannel(channel);
      }
    };
  }, [enabled]);
}
