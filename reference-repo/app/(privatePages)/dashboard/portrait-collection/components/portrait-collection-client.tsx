"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { SegmentIdentificationCard } from "@/app/(privatePages)/dashboard/portrait-collection/components/segment-identification-card";
import { CollectionProgress } from "@/app/(privatePages)/dashboard/portrait-collection/components/collection-progress";
import { CollectionResults } from "@/app/(privatePages)/dashboard/portrait-collection/components/collection-results";
import { ConfirmSubmissionDialog } from "@/app/(privatePages)/dashboard/portrait-collection/components/confirm-submission-dialog";
import { SkipSegmentDialog } from "@/app/(privatePages)/dashboard/portrait-collection/components/skip-segment-dialog";
import { usePortraitCollectionRealtime } from "@/hooks/use-portrait-collection-realtime";
import type {
  UnidentifiedSegment,
  PortraitCollectionStats,
  SelectedMPData,
  SkipReason,
} from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface PortraitCollectionClientProps {
  initialStats: PortraitCollectionStats;
  userId: string;
}

export function PortraitCollectionClient({
  initialStats,
  userId,
}: PortraitCollectionClientProps) {
  const [stats, setStats] = useState<PortraitCollectionStats>(initialStats);
  const [currentSegment, setCurrentSegment] =
    useState<UnidentifiedSegment | null>(null);
  const [selectedFaceIndices, setSelectedFaceIndices] = useState<Set<number>>(
    new Set()
  );
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [skipDialogOpen, setSkipDialogOpen] = useState(false);
  const [evaluatedIds, setEvaluatedIds] = useState<Set<string>>(new Set());
  const [selectedMPData, setSelectedMPData] = useState<SelectedMPData | null>(
    null
  );

  const currentSegmentIdRef = useRef<string | null>(null);

  // Fetch stats to check if truly complete
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch("/api/portrait-collection/stats");
      const data = await response.json();

      if (response.ok && data) {
        setStats(data);
        return data;
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
    return null;
  }, []);

  // Fetch the next segment
  const fetchNextSegment = useCallback(
    async (retryCount = 0) => {
      const MAX_RETRIES = 3;

      setIsLoading(true);
      // Reset selection state
      setSelectedFaceIndices(new Set());
      setSelectedMemberId(null);
      setSelectedMPData(null);

      try {
        const response = await fetch("/api/portrait-collection/next-segment");
        const data = await response.json();

        // Handle 409 Conflict (race condition - segment was just evaluated by another user)
        if (response.status === 409) {
          if (retryCount < MAX_RETRIES) {
            console.log(
              `Segment was just evaluated, retrying (${
                retryCount + 1
              }/${MAX_RETRIES})...`
            );
            // Automatically retry without showing error to user
            return await fetchNextSegment(retryCount + 1);
          } else {
            // Max retries exceeded - treat as all segments being evaluated
            console.log(
              "Max retries exceeded, all segments are currently being evaluated"
            );
            setIsComplete(true);
            setCurrentSegment(null);
            return;
          }
        }

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch segment");
        }

        if (data.complete) {
          // Always check actual stats to determine completion
          // The next-segment API only checks first batch, so we can't trust its completion status
          const latestStats = await fetchStats();

          if (!latestStats) {
            // Failed to fetch stats, don't mark as complete
            setCurrentSegment(null);
            setIsComplete(false);
            toast.error(
              "Failed to fetch collection stats. Please refresh the page."
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
            // The next-segment API couldn't find any in the current batch,
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
    },
    [fetchStats]
  );

  // Unlock current segment on unmount
  const unlockSegment = useCallback((segmentId: string) => {
    try {
      // Use sendBeacon for reliable delivery when page is closing
      // Falls back to fetch for regular cleanup
      const data = JSON.stringify({ segmentId });

      if (navigator.sendBeacon) {
        // sendBeacon guarantees delivery even when page is closing
        const blob = new Blob([data], { type: "application/json" });
        navigator.sendBeacon("/api/portrait-collection/unlock", blob);
      } else {
        // Fallback for browsers that don't support sendBeacon
        fetch("/api/portrait-collection/unlock", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: data,
          keepalive: true, // Keep request alive even if page closes
        }).catch((error) => {
          console.error("Error unlocking segment:", error);
        });
      }
    } catch (error) {
      console.error("Error unlocking segment:", error);
    }
  }, []);

  // Handle face toggle
  const handleFaceToggle = useCallback((faceIndex: number) => {
    setSelectedFaceIndices((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(faceIndex)) {
        newSet.delete(faceIndex);
      } else {
        newSet.add(faceIndex);
      }
      return newSet;
    });
  }, []);

  // Handle MP selection
  const handleMpSelect = useCallback(
    async (memberId: number) => {
      // Toggle selection: if already selected, deselect
      if (selectedMemberId === memberId) {
        setSelectedMemberId(null);
        setSelectedMPData(null);
        return;
      }

      setSelectedMemberId(memberId);

      // Check if MP is in top candidates
      const mpInCandidates = currentSegment?.topCandidates.find(
        (c) => c.memberId === memberId
      );

      if (mpInCandidates) {
        // Use data from top candidates
        setSelectedMPData({
          memberId: mpInCandidates.memberId,
          displayName: mpInCandidates.displayName,
          partyName: mpInCandidates.partyName,
          partyAbbreviation: mpInCandidates.partyAbbreviation,
          constituencyName: mpInCandidates.constituencyName,
          portraits: mpInCandidates.portraits,
        });
      } else {
        // Fetch MP data from API
        try {
          const response = await fetch(`/api/setup/mps?search=${memberId}`);
          const data = await response.json();

          if (data.mps && data.mps.length > 0) {
            const mp = data.mps[0];
            setSelectedMPData({
              memberId: mp.member_id,
              displayName: mp.display_name,
              partyName: mp.party_name,
              partyAbbreviation: mp.party_abbreviation,
              constituencyName: mp.constituency_name,
              portraits: mp.parliament_member_portraits.map(
                (p: { image_url: string; is_primary: boolean | null }) => ({
                  id: crypto.randomUUID(),
                  imageUrl: p.image_url,
                  fallbackUrl: null,
                  isPrimary: p.is_primary,
                })
              ),
            });
          }
        } catch (error) {
          console.error("Error fetching MP data:", error);
        }
      }
    },
    [currentSegment, selectedMemberId]
  );

  // Open confirmation dialog
  const handleSubmit = useCallback(() => {
    if (selectedFaceIndices.size === 0 || selectedMemberId === null) {
      toast.error("Please select at least one face and an MP");
      return;
    }
    setConfirmDialogOpen(true);
  }, [selectedFaceIndices, selectedMemberId]);

  // Confirm and submit identification
  const confirmSubmit = useCallback(async () => {
    if (!currentSegment || selectedMemberId === null) return;

    setIsSubmitting(true);

    try {
      // Get all face indices (both selected and rejected)
      const allFaceIndices = currentSegment.speakerFaces.map(
        (f) => f.faceIndex
      );
      const selectedIndices = Array.from(selectedFaceIndices);
      const rejectedIndices = allFaceIndices.filter(
        (idx) => !selectedFaceIndices.has(idx)
      );

      const response = await fetch("/api/portrait-collection/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segmentId: currentSegment.segmentId,
          selectedMemberId,
          selectedFaceIndices: selectedIndices,
          rejectedFaceIndices: rejectedIndices,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to submit identification");
      }

      // Mark as evaluated
      setEvaluatedIds((prev) => new Set(prev).add(currentSegment.segmentId));

      // Update stats optimistically
      setStats((prev) => ({
        ...prev,
        evaluatedCount: prev.evaluatedCount + 1,
        portraitsAddedCount: prev.portraitsAddedCount + data.portraitCount,
        remainingCount: Math.max(0, prev.remainingCount - 1),
        completionPercentage:
          prev.totalUnidentified > 0
            ? Math.round(
                ((prev.evaluatedCount + 1) / prev.totalUnidentified) * 100
              )
            : 0,
      }));

      toast.success(
        `Successfully added ${data.portraitCount} portrait${
          data.portraitCount !== 1 ? "s" : ""
        }!`
      );

      setConfirmDialogOpen(false);

      // Fetch next segment
      await fetchNextSegment();
    } catch (error) {
      console.error("Error submitting identification:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to submit identification"
      );

      // Rollback optimistic update
      setEvaluatedIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(currentSegment.segmentId);
        return newSet;
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [currentSegment, selectedMemberId, selectedFaceIndices, fetchNextSegment]);

  // Open skip dialog
  const handleSkip = useCallback(() => {
    setSkipDialogOpen(true);
  }, []);

  // Confirm and skip segment
  const confirmSkip = useCallback(
    async (skipReason: SkipReason) => {
      if (!currentSegment) return;

      setIsSubmitting(true);

      try {
        const response = await fetch("/api/portrait-collection/skip", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            segmentId: currentSegment.segmentId,
            skipReason,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to skip segment");
        }

        // Mark as evaluated (skipped)
        setEvaluatedIds((prev) => new Set(prev).add(currentSegment.segmentId));

        // Update stats optimistically
        setStats((prev) => ({
          ...prev,
          evaluatedCount: prev.evaluatedCount + 1,
          remainingCount: Math.max(0, prev.remainingCount - 1),
          completionPercentage:
            prev.totalUnidentified > 0
              ? Math.round(
                  ((prev.evaluatedCount + 1) / prev.totalUnidentified) * 100
                )
              : 0,
        }));

        const skipReasonText =
          skipReason === "bad_quality"
            ? "bad face quality"
            : skipReason === "no_speaker_faces"
            ? "no speaker faces"
            : "already added similar pictures";

        toast.success(`Segment skipped (${skipReasonText})`);

        // Fetch next segment
        await fetchNextSegment();
      } catch (error) {
        console.error("Error skipping segment:", error);

        const errorMessage =
          error instanceof Error ? error.message : "Failed to skip segment";

        toast.error(errorMessage);

        // Rollback optimistic update
        setEvaluatedIds((prev) => {
          const newSet = new Set(prev);
          newSet.delete(currentSegment.segmentId);
          return newSet;
        });

        // If the error is "already skipped", move to next segment anyway
        if (errorMessage.includes("already been skipped")) {
          await fetchNextSegment();
        }
      } finally {
        setIsSubmitting(false);
        setSkipDialogOpen(false);
      }
    },
    [currentSegment, fetchNextSegment]
  );

  // Initial fetch
  useEffect(() => {
    fetchNextSegment();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount and page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (currentSegmentIdRef.current) {
        unlockSegment(currentSegmentIdRef.current);
      }
    };

    // Add beforeunload listener for when user closes tab/window
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      // Cleanup on component unmount
      if (currentSegmentIdRef.current) {
        unlockSegment(currentSegmentIdRef.current);
      }
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [unlockSegment]);

  // Realtime updates
  usePortraitCollectionRealtime({
    onEvaluationAdded: useCallback(
      (evaluation) => {
        // Only process if not already tracked
        if (evaluatedIds.has(evaluation.segment_id)) return;

        // Don't count our own submissions (already handled optimistically)
        if (evaluation.evaluated_by === userId) return;

        // Add to evaluated set
        setEvaluatedIds((prev) => new Set(prev).add(evaluation.segment_id));

        // Show toast notification
        const portraitCount = evaluation.portraits_added?.length ?? 0;
        toast.info(
          `Another user identified a segment and added ${portraitCount} portrait${
            portraitCount !== 1 ? "s" : ""
          }`
        );

        // Fetch updated stats
        fetchStats();
      },
      [evaluatedIds, userId, fetchStats]
    ),
    enabled: !isComplete,
  });

  // Use stored MP data or find in top candidates
  const selectedMP = selectedMPData;

  const selectedFaces =
    currentSegment?.speakerFaces.filter((f) =>
      selectedFaceIndices.has(f.faceIndex)
    ) ?? [];

  // Loading state
  if (isLoading && !currentSegment) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Completion state
  if (isComplete) {
    return <CollectionResults stats={stats} />;
  }

  return (
    <div className="space-y-6">
      {/* Current Segment */}
      {currentSegment && (
        <SegmentIdentificationCard
          segment={currentSegment}
          selectedFaceIndices={selectedFaceIndices}
          selectedMemberId={selectedMemberId}
          onFaceToggle={handleFaceToggle}
          onMpSelect={handleMpSelect}
          onSubmit={handleSubmit}
          onSkip={handleSkip}
          isSubmitting={isSubmitting}
        />
      )}

      {/* Transcript */}
      {currentSegment?.transcript && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Transcript</h3>
          <div className="rounded-lg border border-border bg-muted/50 p-4">
            <p className="text-sm leading-relaxed">
              {currentSegment.transcript}
            </p>
          </div>
        </div>
      )}

      {/* Progress Stats */}
      <CollectionProgress stats={stats} />

      {/* Confirmation Dialog */}
      <ConfirmSubmissionDialog
        open={confirmDialogOpen}
        onOpenChange={setConfirmDialogOpen}
        selectedMP={selectedMP ?? null}
        selectedFaces={selectedFaces}
        isSubmitting={isSubmitting}
        onConfirm={confirmSubmit}
        sessionDate={currentSegment?.sessionDate ?? null}
      />

      {/* Skip Segment Dialog */}
      <SkipSegmentDialog
        open={skipDialogOpen}
        onOpenChange={setSkipDialogOpen}
        isSubmitting={isSubmitting}
        onConfirm={confirmSkip}
      />
    </div>
  );
}
