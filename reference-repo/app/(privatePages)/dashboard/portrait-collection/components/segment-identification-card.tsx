"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import NativeVideoPlayer from "@/components/ui/native-video-player";
import { FaceSelectionGrid } from "@/app/(privatePages)/dashboard/portrait-collection/components/face-selection-grid";
import { MpCandidatesList } from "@/app/(privatePages)/dashboard/portrait-collection/components/mp-candidates-list";
import { TopCandidateCard } from "@/app/(privatePages)/dashboard/portrait-collection/components/top-candidate-card";
import { MpSearchPanel } from "@/app/(privatePages)/dashboard/portrait-collection/components/mp-search-panel";
import type { UnidentifiedSegment } from "@/app/(privatePages)/dashboard/portrait-collection/constants";
import { formatSecondsToTime, addSecondsToTime } from "@/lib/formatTime";

interface SegmentIdentificationCardProps {
  segment: UnidentifiedSegment;
  selectedFaceIndices: Set<number>;
  selectedMemberId: number | null;
  onFaceToggle: (faceIndex: number) => void;
  onMpSelect: (memberId: number) => void;
  onSubmit: () => void;
  onSkip: () => void;
  isSubmitting: boolean;
}

export function SegmentIdentificationCard({
  segment,
  selectedFaceIndices,
  selectedMemberId,
  onFaceToggle,
  onMpSelect,
  onSubmit,
  onSkip,
  isSubmitting,
}: SegmentIdentificationCardProps) {
  const isValid = selectedFaceIndices.size > 0 && selectedMemberId !== null;

  // Calculate event URL with timestamp parameter
  const timestamp = addSecondsToTime(
    segment.sessionStartTime,
    segment.startSeconds
  );
  const eventUrlWithTimestamp =
    segment.eventUrl && timestamp
      ? `${segment.eventUrl}?in=${timestamp}`
      : segment.eventUrl;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Identify the MP Speaking</CardTitle>
        {(segment.sessionDate ||
          segment.startSeconds !== null ||
          segment.endSeconds !== null ||
          segment.eventUrl) && (
          <div className="text-sm text-muted-foreground mt-1 space-y-0.5">
            {segment.sessionDate && (
              <p>
                Session:{" "}
                {new Date(segment.sessionDate).toLocaleDateString("en-GB", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            )}
            {(segment.startSeconds !== null || segment.endSeconds !== null) && (
              <p>
                Time:{" "}
                {segment.startSeconds !== null &&
                  formatSecondsToTime(segment.startSeconds)}
                {segment.startSeconds !== null &&
                  segment.endSeconds !== null &&
                  " - "}
                {segment.endSeconds !== null &&
                  formatSecondsToTime(segment.endSeconds)}
              </p>
            )}
            {eventUrlWithTimestamp && (
              <p>
                <a
                  href={eventUrlWithTimestamp}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline inline-flex items-center gap-1"
                >
                  View Parliament Event
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </p>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Video Player */}
        {segment.clipUrl && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Video Clip</h3>
            <NativeVideoPlayer
              src={segment.clipUrl}
              poster={segment.thumbnailUrl ?? undefined}
              className="w-full rounded-lg"
            />
          </div>
        )}

        <Separator />

        {/* Step 1 and Step 2 Side by Side */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Step 1: Face Selection - Left Side */}
          <div className="space-y-3">
            <div className="space-y-1">
              <h3 className="text-sm font-medium">
                Step 1: Select the MP&apos;s face(s)
              </h3>
              <p className="text-sm text-muted-foreground">
                Click on the faces that show the MP speaking. You can select
                multiple faces.
              </p>
            </div>
            <FaceSelectionGrid
              faces={segment.speakerFaces}
              selectedIndices={selectedFaceIndices}
              onToggle={onFaceToggle}
              onMpSelect={onMpSelect}
            />
            {selectedFaceIndices.size > 0 && (
              <p className="text-sm text-primary">
                ✓ {selectedFaceIndices.size} face
                {selectedFaceIndices.size !== 1 ? "s" : ""} selected
              </p>
            )}
          </div>

          {/* Step 2: Top Candidates - Right Side */}
          <div className="space-y-3">
            {segment.topCandidates.length > 0 ? (
              <>
                <div className="space-y-1">
                  <h3 className="text-sm font-medium">
                    Step 2: Identify the MP
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Top candidates - compare with selected faces
                  </p>
                </div>
                <div className="space-y-4">
                  {segment.topCandidates.slice(0, 3).map((candidate) => (
                    <TopCandidateCard
                      key={candidate.memberId}
                      candidate={candidate}
                      selectedMemberId={selectedMemberId}
                      onSelect={onMpSelect}
                      sessionDate={segment.sessionDate}
                    />
                  ))}
                </div>
              </>
            ) : (
              <div className="space-y-1">
                <h3 className="text-sm font-medium">Step 2: Identify the MP</h3>
                <p className="text-sm text-muted-foreground">
                  No top candidate found. Use search below.
                </p>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Additional Candidates and Search */}
        <div className="space-y-3">
          {/* Other Candidates (if more than 3) */}
          {segment.topCandidates.length > 3 && (
            <div className="space-y-3">
              <p className="text-sm font-medium">
                Other Candidates ({segment.topCandidates.length - 3})
              </p>
              <MpCandidatesList
                candidates={segment.topCandidates.slice(3)}
                selectedMemberId={selectedMemberId}
                onSelect={onMpSelect}
                sessionDate={segment.sessionDate}
              />
            </div>
          )}

          {/* Search Panel */}
          <MpSearchPanel
            selectedMemberId={selectedMemberId}
            onSelect={onMpSelect}
            defaultOpen={segment.topCandidates.length === 0}
            sessionDate={segment.sessionDate}
          />

          {selectedMemberId && (
            <p className="text-sm text-primary">✓ MP selected</p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          <Button
            onClick={onSubmit}
            disabled={!isValid || isSubmitting}
            className="w-full"
            size="lg"
          >
            {isSubmitting ? "Submitting..." : "Submit Identification"}
          </Button>

          <Button
            onClick={onSkip}
            disabled={isSubmitting}
            variant="outline"
            className="w-full"
            size="lg"
          >
            Skip This Segment
          </Button>

          {!isValid && (
            <p className="text-center text-sm text-muted-foreground">
              {selectedFaceIndices.size === 0
                ? "Select at least one face to continue, or skip this segment"
                : "Select an MP to continue, or skip this segment"}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
