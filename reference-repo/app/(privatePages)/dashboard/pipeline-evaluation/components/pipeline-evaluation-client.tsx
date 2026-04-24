"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { SegmentEvaluationCard } from "./segment-evaluation-card";
import { EvaluationProgress } from "./evaluation-progress";
import { EvaluationResults } from "./evaluation-results";
import { WrongMpDialog } from "./wrong-mp-dialog";
import { useSegmentEvaluationRealtime } from "@/hooks/use-segment-evaluation-realtime";
import type {
  EvaluableSegment,
  EvaluationStats,
  ErrorReason,
} from "../constants";

interface PipelineEvaluationClientProps {
  initialStats: EvaluationStats;
  userId: string;
}

export function PipelineEvaluationClient({
  initialStats,
  userId,
}: PipelineEvaluationClientProps) {
  const [stats, setStats] = useState<EvaluationStats>(initialStats);
  const [currentSegment, setCurrentSegment] = useState<EvaluableSegment | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [wrongDialogOpen, setWrongDialogOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [evaluatedIds, setEvaluatedIds] = useState<Set<string>>(new Set());

  const switchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentSegmentIdRef = useRef<string | null>(null);

  // Fetch stats to check if truly complete
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch("/api/pipeline-evaluation/stats");
      const data = await response.json();

      if (response.ok && data.stats) {
        setStats(data.stats);
        return data.stats;
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
    return null;
  }, []);

  // Fetch the next segment
  const fetchNextSegment = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/pipeline-evaluation/next-segment");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch segment");
      }

      if (data.complete) {
        // Always check actual stats to determine completion
        // The next-segment API only checks first 1000 segments, so we can't trust its completion status
        const latestStats = await fetchStats();

        if (!latestStats) {
          // Failed to fetch stats, don't mark as complete
          setCurrentSegment(null);
          setIsComplete(false);
          toast.error(
            "Failed to fetch evaluation stats. Please refresh the page."
          );
          return;
        }

        // Only mark as complete if there are truly no remaining segments
        if (latestStats.remainingCount === 0) {
          // Truly complete - all segments evaluated
          setIsComplete(true);
          setCurrentSegment(null);
        } else {
          // There are still segments to evaluate
          // The next-segment API couldn't find any in the first 1000 it checked,
          // but there are more segments available
          setCurrentSegment(null);
          setIsComplete(false);
          toast.info(
            `No segments available in current batch. ${latestStats.remainingCount} segments remaining.`,
            {
              duration: 5000,
              action: {
                label: "Retry",
                onClick: () => fetchNextSegment(),
              },
            }
          );
        }
      } else if (data.segment) {
        // Trigger switching delay if we had a previous segment
        if (currentSegmentIdRef.current) {
          setIsSwitching(true);
          if (switchTimerRef.current) {
            clearTimeout(switchTimerRef.current);
          }
          switchTimerRef.current = setTimeout(() => {
            setIsSwitching(false);
            switchTimerRef.current = null;
          }, 2000);
        }

        currentSegmentIdRef.current = data.segment.segmentId;
        setCurrentSegment(data.segment);
        setIsComplete(false);
      }
    } catch (error) {
      console.error("Error fetching next segment:", error);
      toast.error("Failed to fetch next segment");
    } finally {
      setIsLoading(false);
    }
  }, [fetchStats]);

  // Unlock current segment on unmount
  const unlockSegment = useCallback(async (segmentId: string) => {
    try {
      await fetch("/api/pipeline-evaluation/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segmentId }),
      });
    } catch (error) {
      console.error("Error unlocking segment:", error);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchNextSegment();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (switchTimerRef.current) {
        clearTimeout(switchTimerRef.current);
      }
      // Unlock current segment on unmount
      if (currentSegmentIdRef.current) {
        unlockSegment(currentSegmentIdRef.current);
      }
    };
  }, [unlockSegment]);

  // Handle realtime updates
  useSegmentEvaluationRealtime({
    onEvaluationAdded: (evaluation) => {
      // Skip if this is our own evaluation (check both evaluatedIds and evaluated_by)
      if (
        evaluatedIds.has(evaluation.segment_id) ||
        evaluation.evaluated_by === userId
      ) {
        return;
      }

      // Update local state
      setEvaluatedIds((prev) => new Set(prev).add(evaluation.segment_id));

      // Update stats
      setStats((prev) => {
        const newStats = { ...prev };
        newStats.evaluatedCount += 1;
        newStats.remainingCount -= 1;

        if (evaluation.is_correct) {
          newStats.correctCount += 1;
        } else if (evaluation.error_reason === "wrong_speaker_detected") {
          newStats.wrongSpeakerCount += 1;
        } else if (evaluation.error_reason === "wrong_mp_matched") {
          newStats.wrongMpCount += 1;
        }

        newStats.accuracyPercentage =
          newStats.evaluatedCount > 0
            ? Math.round(
                (newStats.correctCount / newStats.evaluatedCount) * 10000
              ) / 100
            : 0;

        if (newStats.remainingCount === 0) {
          setIsComplete(true);
        }

        return newStats;
      });

      // Show toast notification
      toast.info("Another evaluator submitted an evaluation");
    },
    enabled: !isComplete,
  });

  // Submit evaluation
  const submitEvaluation = useCallback(
    async (isCorrect: boolean, errorReason?: ErrorReason) => {
      if (!currentSegment || isSubmitting) return;

      // Optimistically update evaluatedIds BEFORE API call to prevent race condition
      // with realtime subscription
      setEvaluatedIds((prev) => new Set(prev).add(currentSegment.segmentId));

      setIsSubmitting(true);
      try {
        const response = await fetch("/api/pipeline-evaluation/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            segmentId: currentSegment.segmentId,
            isCorrect,
            errorReason,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to submit evaluation");
        }

        // Update stats locally
        setStats((prev) => {
          const newStats = { ...prev };
          newStats.evaluatedCount += 1;
          newStats.remainingCount -= 1;

          if (isCorrect) {
            newStats.correctCount += 1;
          } else if (errorReason === "wrong_speaker_detected") {
            newStats.wrongSpeakerCount += 1;
          } else if (errorReason === "wrong_mp_matched") {
            newStats.wrongMpCount += 1;
          }

          newStats.accuracyPercentage =
            newStats.evaluatedCount > 0
              ? Math.round(
                  (newStats.correctCount / newStats.evaluatedCount) * 10000
                ) / 100
              : 0;

          return newStats;
        });

        toast.success(isCorrect ? "Marked as correct" : "Marked as incorrect");

        // Fetch next segment
        await fetchNextSegment();
      } catch (error) {
        console.error("Error submitting evaluation:", error);
        toast.error(
          error instanceof Error ? error.message : "Failed to submit evaluation"
        );
        // Rollback optimistic update on error
        setEvaluatedIds((prev) => {
          const newSet = new Set(prev);
          newSet.delete(currentSegment.segmentId);
          return newSet;
        });
      } finally {
        setIsSubmitting(false);
        setWrongDialogOpen(false);
      }
    },
    [currentSegment, isSubmitting, fetchNextSegment]
  );

  // Handle correct button
  const handleCorrect = useCallback(() => {
    submitEvaluation(true);
  }, [submitEvaluation]);

  // Handle wrong button
  const handleWrong = useCallback(() => {
    setWrongDialogOpen(true);
  }, []);

  // Handle wrong dialog submit
  const handleWrongSubmit = useCallback(
    (reason: ErrorReason) => {
      submitEvaluation(false, reason);
    },
    [submitEvaluation]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger if typing in an input
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      // Don't trigger if dialog is open, loading, submitting, or switching
      if (
        wrongDialogOpen ||
        isLoading ||
        isSubmitting ||
        isSwitching ||
        !currentSegment
      ) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case "q":
          event.preventDefault();
          handleCorrect();
          break;
        case "w":
          event.preventDefault();
          handleWrong();
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    wrongDialogOpen,
    isLoading,
    isSubmitting,
    isSwitching,
    currentSegment,
    handleCorrect,
    handleWrong,
  ]);

  // Show loading state
  if (isLoading && !currentSegment) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
          <p className="text-muted-foreground">Loading next segment...</p>
        </div>
      </div>
    );
  }

  // Show completion state
  if (isComplete) {
    return (
      <div className="space-y-6">
        <EvaluationProgress stats={stats} />
        <EvaluationResults stats={stats} />
      </div>
    );
  }

  // Show evaluation UI
  return (
    <div className="space-y-6">
      {/* Progress */}
      <EvaluationProgress stats={stats} />

      {/* Current segment evaluation */}
      {currentSegment && (
        <SegmentEvaluationCard
          key={currentSegment.segmentId}
          segment={currentSegment}
          onCorrect={handleCorrect}
          onWrong={handleWrong}
          isSubmitting={isSubmitting}
          isDisabled={isSwitching || isLoading}
        />
      )}

      {/* Wrong MP dialog */}
      <WrongMpDialog
        open={wrongDialogOpen}
        onOpenChange={setWrongDialogOpen}
        onSubmit={handleWrongSubmit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
