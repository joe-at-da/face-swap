"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  Check,
  Video,
  Smartphone,
} from "lucide-react";

interface ClipProcessingStatusProps {
  status: string;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  clip_url: string | null;
  vertical_clip_url: string | null;
}

export function ClipProcessingStatus({
  status,
  created_at: _created_at,
  updated_at: _updated_at,
  error_message,
  clip_url,
  vertical_clip_url,
}: ClipProcessingStatusProps) {
  return (
    <Card className="border overflow-hidden mt-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3 text-xl">
            <div
              className={`p-1 rounded bg-primary/10 ${
                status === "processing" ? "animate-pulse" : ""
              }`}
            >
              <Loader2
                className={`h-5 w-5 text-primary ${
                  status === "processing" ? "animate-spin" : ""
                }`}
              />
            </div>
            <span>Processing Status</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        {/* Error Message */}
        {status === "failed" && error_message && (
          <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-destructive/10 to-destructive/5 border-2 border-destructive/30 p-5 shadow-sm">
            <div className="absolute top-0 right-0 w-32 h-32 bg-destructive/10 rounded-full -mr-16 -mt-16 blur-2xl" />
            <div className="relative flex items-start gap-4">
              <div className="p-3 rounded-full bg-destructive/10 ring-4 ring-destructive/5">
                <AlertCircle className="h-6 w-6 text-destructive" />
              </div>
              <div className="flex-1 space-y-2">
                <div className="text-sm font-bold text-destructive uppercase tracking-wide">
                  Processing Failed
                </div>
                <div className="text-sm text-destructive/90 leading-relaxed">
                  {error_message}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Completion Status */}
        {status === "completed" && (
          <div className="space-y-5">
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-2 border-green-200 dark:border-green-800 p-5 shadow-sm">
              <div className="absolute top-0 right-0 w-32 h-32 bg-green-200/20 dark:bg-green-800/20 rounded-full -mr-16 -mt-16 blur-2xl" />
              <div className="relative flex items-center gap-4">
                <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/50 ring-4 ring-green-100/50 dark:ring-green-900/30">
                  <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-bold text-foreground uppercase tracking-wide mb-1">
                    Processing Complete!
                  </div>
                  <div className="text-sm text-foreground">
                    Your clips are ready to view and share.
                  </div>
                </div>
              </div>
            </div>

            {/* Available Formats */}
            <div className="grid grid-cols-2 gap-4">
              <div
                className={`group relative overflow-hidden p-4 rounded-xl border-2 transition-all duration-300 ${
                  clip_url
                    ? "bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-green-300 dark:border-green-700 shadow-sm hover:shadow-md hover:scale-[1.02]"
                    : "bg-muted/50 border-muted-foreground/30 hover:border-muted-foreground/50"
                }`}
              >
                <div className="relative flex flex-col space-y-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        clip_url
                          ? "bg-green-100 dark:bg-green-900/50"
                          : "bg-muted"
                      }`}
                    >
                      <Video
                        className={`h-5 w-5 ${
                          clip_url
                            ? "text-green-600 dark:text-green-400"
                            : "text-muted-foreground"
                        }`}
                      />
                    </div>
                    <span className="text-sm font-semibold">Horizontal</span>
                  </div>
                  <div>
                    {clip_url ? (
                      <Badge className="bg-green-600 dark:bg-green-700 text-white shadow-sm">
                        ✓ Ready
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="animate-pulse">
                        Processing...
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <div
                className={`group relative overflow-hidden p-4 rounded-xl border-2 transition-all duration-300 ${
                  vertical_clip_url
                    ? "bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-green-300 dark:border-green-700 shadow-sm hover:shadow-md hover:scale-[1.02]"
                    : "bg-muted/50 border-muted-foreground/30 hover:border-muted-foreground/50"
                }`}
              >
                <div className="relative flex flex-col space-y-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        vertical_clip_url
                          ? "bg-green-100 dark:bg-green-900/50"
                          : "bg-muted"
                      }`}
                    >
                      <Smartphone
                        className={`h-5 w-5 ${
                          vertical_clip_url
                            ? "text-green-600 dark:text-green-400"
                            : "text-muted-foreground"
                        }`}
                      />
                    </div>
                    <span className="text-sm font-semibold">Vertical</span>
                  </div>
                  <div>
                    {vertical_clip_url ? (
                      <Badge className="bg-green-600 dark:bg-green-700 text-white shadow-sm">
                        ✓ Ready
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="animate-pulse">
                        Processing...
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Processing Steps */}
        {(status === "processing" || status === "pending_review") && (
          <div className="relative">
            {/* Continuous unbroken connecting line - centered on circles */}
            <div
              className="absolute top-[10px] left-[10%] h-0.5 bg-muted-foreground/30"
              style={{ width: "80%" }}
            >
              {/* Primary portion for completed steps and line segment before next incomplete step */}
              {(() => {
                const steps = [
                  { step: "Queue", completed: true },
                  { step: "Analysis", completed: status !== "pending_review" },
                  { step: "Generation", completed: false },
                  { step: "Optimization", completed: false },
                  { step: "Finalization", completed: false },
                ];
                // Find the last completed step
                const lastCompletedIndex = steps.findLastIndex(
                  (s) => s.completed
                );

                // Line starts at 10% (center of first step) and ends at 90% (center of last step)
                // So the available width is 80% (90% - 10%)
                const lineStartPercent = 10; // Center of first step
                const lineEndPercent = 90; // Center of last step
                const availableWidth = lineEndPercent - lineStartPercent; // 80%

                // Find the first incomplete step (next step)
                const nextIncompleteIndex = steps.findIndex(
                  (s) => !s.completed
                );

                // If no steps are completed, show no progress
                if (lastCompletedIndex < 0) {
                  return null;
                }

                // If all are completed, show full available width (80%)
                if (lastCompletedIndex === steps.length - 1) {
                  return (
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${availableWidth}%` }}
                    />
                  );
                }

                // Calculate width: up to the center of the next incomplete step circle
                // This includes the FULL line segment after the last completed step up to the next step
                // The line container starts at 10% and has width 80% (from 10% to 90%)
                // Position of next incomplete step center in full width: (nextIncompleteIndex * 20%) + 10%
                // Position relative to container start: nextIncompleteCenter - 10%
                // As percentage of container (80%): (nextIncompleteCenter - 10%) / 80% * 100
                const nextIncompleteCenter =
                  (nextIncompleteIndex / steps.length) * 100 +
                  100 / steps.length / 2;
                // Calculate width relative to the container (which is 80% of full width)
                const progressWidthPercent =
                  ((nextIncompleteCenter - lineStartPercent) / availableWidth) *
                  100;
                const progressWidth = Math.min(progressWidthPercent, 100);

                return (
                  <div
                    className="h-full bg-primary transition-all"
                    style={{
                      width: `${progressWidth}%`,
                    }}
                  />
                );
              })()}
            </div>

            {/* Circles and names */}
            <div className="flex items-start">
              {(() => {
                const steps = [
                  { step: "Queue", completed: true },
                  { step: "Analysis", completed: status !== "pending_review" },
                  { step: "Generation", completed: false },
                  { step: "Optimization", completed: false },
                  { step: "Done", completed: false },
                ];
                const nextIncompleteIndex = steps.findIndex(
                  (s) => !s.completed
                );

                return steps.map((item, index) => {
                  const isNextIncomplete = index === nextIncompleteIndex;
                  return (
                    <div
                      key={index}
                      className="flex flex-col items-center gap-2 flex-1"
                    >
                      <div
                        className={`flex items-center justify-center w-5 h-5 rounded-full transition-all relative z-10 ${
                          item.completed
                            ? "bg-primary"
                            : isNextIncomplete
                            ? "bg-white border border-primary"
                            : "bg-white border border-muted-foreground/30"
                        }`}
                      >
                        {item.completed ? (
                          <Check className="w-3 h-3 text-white" />
                        ) : isNextIncomplete ? (
                          <div className="w-2 h-2 bg-primary rounded-full" />
                        ) : (
                          <div className="w-2 h-2 bg-white rounded-full" />
                        )}
                      </div>
                      <span
                        className={`text-xs text-center ${
                          item.completed
                            ? "text-foreground font-medium"
                            : "text-muted-foreground"
                        }`}
                      >
                        {item.step}
                      </span>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Export estimated time component separately
export function ClipProcessingEstimatedTime({
  status,
  remainingSeconds,
}: {
  status: string;
  remainingSeconds: number;
}) {
  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return "Almost done!";
    const minutes = Math.floor(seconds / 60);
    const remainingSecs = seconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${remainingSecs}s`;
    }
    return `${remainingSecs}s`;
  };

  const getEstimatedTime = (status: string) => {
    if (status === "completed" || status === "failed") return null;

    if (status === "pending_review") {
      return "Processing will begin shortly";
    }

    if (status === "processing") {
      return formatTimeRemaining(remainingSeconds);
    }

    return null;
  };

  const estimatedTime = getEstimatedTime(status);

  if (!estimatedTime) return null;

  return (
    <div className="rounded-lg p-3 text-center bg-[#DBEAFE]">
      <p className="text-sm text-[#1E40AF]">{estimatedTime}</p>
    </div>
  );
}
