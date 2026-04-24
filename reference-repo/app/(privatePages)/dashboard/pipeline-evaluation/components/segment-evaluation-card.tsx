"use client";

import NativeVideoPlayer from "@/components/ui/native-video-player";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Check, X, Loader2 } from "lucide-react";
import { SpeakerFacesGrid } from "./speaker-faces-grid";
import { MPPortraitsGrid } from "./mp-portraits-grid";
import type { EvaluableSegment } from "../constants";
import { addSecondsToTime } from "@/lib/formatTime";

interface SegmentEvaluationCardProps {
  segment: EvaluableSegment;
  onCorrect: () => void;
  onWrong: () => void;
  isSubmitting: boolean;
  isDisabled: boolean;
}

export function SegmentEvaluationCard({
  segment,
  onCorrect,
  onWrong,
  isSubmitting,
  isDisabled,
}: SegmentEvaluationCardProps) {
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
    <div className="space-y-6">
      {/* Video Player */}
      <Card>
        <CardContent className="pt-6">
          {segment.clipUrl ? (
            <NativeVideoPlayer
              src={segment.clipUrl}
              poster={segment.thumbnailUrl}
              className="w-full"
            />
          ) : (
            <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
              <p className="text-muted-foreground">No video available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Transcript */}
      {segment.transcript && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-foreground mb-2">
              Transcript
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              &ldquo;{segment.transcript}&rdquo;
            </p>
          </CardContent>
        </Card>
      )}

      {/* Event URL Link */}
      {eventUrlWithTimestamp && (
        <div className="text-sm text-muted-foreground">
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              window.open(
                eventUrlWithTimestamp,
                "_blank",
                "noopener,noreferrer"
              );
            }}
            className="text-primary hover:underline inline-flex items-center gap-1 cursor-pointer bg-transparent border-none p-0"
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
          </button>
        </div>
      )}

      {/* Faces and Portraits Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Speaker Faces */}
        <Card>
          <CardContent className="pt-6">
            <SpeakerFacesGrid faces={segment.speakerFaces} />
          </CardContent>
        </Card>

        {/* MP Portraits */}
        <Card>
          <CardContent className="pt-6">
            <MPPortraitsGrid
              portraits={segment.mpPortraits}
              memberName={segment.memberName}
              partyName={segment.partyName}
              constituencyName={segment.constituencyName}
            />
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button
          onClick={onCorrect}
          disabled={isDisabled || isSubmitting}
          className="flex-1"
          size="lg"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              <Check className="h-4 w-4 mr-2" />
              Correct MP
            </>
          )}
        </Button>

        <Button
          onClick={onWrong}
          disabled={isDisabled || isSubmitting}
          variant="destructive"
          className="flex-1"
          size="lg"
        >
          <X className="h-4 w-4 mr-2" />
          Wrong MP
        </Button>
      </div>

      {/* Keyboard shortcut hint */}
      <p className="text-xs text-muted-foreground text-center">
        Press <kbd className="px-1 bg-muted rounded">Q</kbd> for Correct,{" "}
        <kbd className="px-1 bg-muted rounded">W</kbd> for Wrong
      </p>
    </div>
  );
}
