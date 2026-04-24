"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import NativeVideoPlayer from "@/components/ui/native-video-player";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ERROR_REASONS } from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";
import type {
  FailedEvaluationResult,
  SpeakerFace,
} from "@/app/api/pipeline-evaluation/results/route";

function getErrorReasonLabel(errorReason: string | null): string {
  if (!errorReason) return "Unknown Error";
  if (errorReason === "wrong_speaker_detected") {
    return ERROR_REASONS.wrong_speaker_detected.label;
  }
  if (errorReason === "wrong_mp_matched") {
    return ERROR_REASONS.wrong_mp_matched.label;
  }
  return errorReason;
}

function getMpIdReasonLabel(mpIdReason: string | null): {
  label: string;
  isPropagated: boolean;
  detail: string;
} {
  if (!mpIdReason) {
    return {
      label: "Unknown Method",
      isPropagated: false,
      detail: "No identification method recorded",
    };
  }

  const reason = mpIdReason.toLowerCase();

  // Check if it's a propagation reason
  if (reason.includes("propagat")) {
    return {
      label: "Propagated",
      isPropagated: true,
      detail: "MP ID copied from nearby segment",
    };
  }

  // Check for direct face match reasons
  if (reason.includes("face") || reason.includes("match")) {
    return {
      label: "Face Match",
      isPropagated: false,
      detail: "Direct facial recognition match",
    };
  }

  // Handle specific reasons
  if (reason === "too_short") {
    return {
      label: "Face Match",
      isPropagated: false,
      detail: "Segment too short for full analysis",
    };
  }

  if (reason === "no_faces") {
    return {
      label: "No Faces",
      isPropagated: false,
      detail: "No faces detected in segment",
    };
  }

  // Default case - show the raw reason
  return {
    label: mpIdReason,
    isPropagated: false,
    detail: mpIdReason,
  };
}

function SpeakerFacesGrid({ faces }: { faces: SpeakerFace[] }) {
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    () => {
      const initial: Record<string, boolean> = {};
      faces.forEach((face) => {
        initial[face.id] = true;
      });
      return initial;
    }
  );
  const [errorStates, setErrorStates] = useState<Record<string, boolean>>({});

  // Reset states when faces change
  useEffect(() => {
    const newLoadingStates: Record<string, boolean> = {};
    const newErrorStates: Record<string, boolean> = {};
    faces.forEach((face) => {
      newLoadingStates[face.id] = true;
      newErrorStates[face.id] = false;
    });
    setLoadingStates(newLoadingStates);
    setErrorStates(newErrorStates);
  }, [faces]);

  const handleImageLoad = (id: string) => {
    setLoadingStates((prev) => ({ ...prev, [id]: false }));
    setErrorStates((prev) => ({ ...prev, [id]: false }));
  };

  const handleImageError = (id: string) => {
    setLoadingStates((prev) => ({ ...prev, [id]: false }));
    setErrorStates((prev) => ({ ...prev, [id]: true }));
  };

  if (faces.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted/50 p-4 text-center">
        <p className="text-sm text-muted-foreground">No faces detected</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
      {faces.map((face) => {
        const isLoading = loadingStates[face.id];
        const hasError = errorStates[face.id];

        return (
          <div
            key={face.id}
            className="relative aspect-square overflow-hidden rounded-lg border border-border bg-muted"
          >
            {isLoading && !hasError && (
              <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            )}
            {hasError ? (
              <div className="absolute inset-0 flex items-center justify-center bg-muted">
                <div className="text-center p-4">
                  <p className="text-xs text-muted-foreground">
                    Failed to load image
                  </p>
                </div>
              </div>
            ) : (
              <img
                src={face.s3Url}
                alt={`Face ${face.faceIndex + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
                loading="lazy"
                onLoad={() => handleImageLoad(face.id)}
                onError={() => handleImageError(face.id)}
              />
            )}
            {/* Face Index Badge */}
            {!hasError && (
              <div className="absolute left-2 top-2">
                <Badge variant="secondary" className="text-xs">
                  Face {face.faceIndex + 1}
                </Badge>
              </div>
            )}
            {/* Quality Score Badge */}
            {face.qualityScore !== null && !hasError && (
              <div className="absolute right-2 top-2">
                <Badge variant="outline" className="bg-background/80 text-xs">
                  {Math.round(face.qualityScore * 100)}%
                </Badge>
              </div>
            )}
            {/* Frontal Badge */}
            {face.isFrontal && !hasError && (
              <div className="absolute bottom-2 left-2">
                <Badge variant="outline" className="bg-background/80 text-xs">
                  Frontal
                </Badge>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function PipelineEvaluationResultsClient() {
  const [results, setResults] = useState<FailedEvaluationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<
    "all" | "wrong_speaker" | "wrong_match"
  >("all");

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      setIsLoading(true);
      const response = await fetch("/api/pipeline-evaluation/results");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch results");
      }

      setResults(data.results || []);
    } catch (error) {
      console.error("Error fetching results:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to fetch results"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const wrongSpeakerResults = results.filter(
    (r) => r.errorReason === "wrong_speaker_detected"
  );
  const wrongMatchResults = results.filter(
    (r) => r.errorReason === "wrong_mp_matched"
  );

  const currentResults =
    selectedTab === "wrong_speaker"
      ? wrongSpeakerResults
      : selectedTab === "wrong_match"
      ? wrongMatchResults
      : results;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Pipeline Evaluation Results</h1>
          <p className="text-muted-foreground mt-2">Loading results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Pipeline Evaluation Results</h1>
        <p className="text-muted-foreground mt-2">
          Review failed evaluations to identify patterns and improve the
          pipeline
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{results.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Wrong Speaker
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {wrongSpeakerResults.length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Wrong Match
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{wrongMatchResults.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Results List */}
      <Tabs
        value={selectedTab}
        onValueChange={(v) => setSelectedTab(v as typeof selectedTab)}
      >
        <TabsList>
          <TabsTrigger value="all">All ({results.length})</TabsTrigger>
          <TabsTrigger value="wrong_speaker">
            Wrong Speaker ({wrongSpeakerResults.length})
          </TabsTrigger>
          <TabsTrigger value="wrong_match">
            Wrong Match ({wrongMatchResults.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={selectedTab} className="mt-6 space-y-4">
          {currentResults.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No failed evaluations found
                </p>
              </CardContent>
            </Card>
          ) : (
            currentResults.map((result) => (
              <Card key={result.segmentId}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base">
                        Segment {result.segmentId.slice(0, 8)}...
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            result.errorReason === "wrong_speaker_detected"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {getErrorReasonLabel(result.errorReason)}
                        </Badge>
                        {result.evaluatedAt && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(result.evaluatedAt).toLocaleString(
                              "en-GB"
                            )}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Video and Transcript */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {result.clipUrl && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Video Clip</h4>
                        <NativeVideoPlayer
                          src={result.clipUrl}
                          poster={result.thumbnailUrl ?? undefined}
                          className="w-full rounded-lg"
                        />
                      </div>
                    )}
                    {result.transcript && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Transcript</h4>
                        <div className="rounded-lg border border-border bg-muted/50 p-4 max-h-48 overflow-y-auto">
                          <p className="text-sm leading-relaxed">
                            {result.transcript}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Speaker Faces */}
                  {result.speakerFaces.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium">Detected Faces</h4>
                      <SpeakerFacesGrid faces={result.speakerFaces} />
                    </div>
                  )}

                  {/* Detection Details */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Detection Details</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Detected Speaker */}
                      <div className="rounded-lg border border-border bg-card p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <h5 className="text-sm font-medium">
                            Detected Speaker
                          </h5>
                          <Badge
                            variant="outline"
                            className="bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20"
                          >
                            Transcript
                          </Badge>
                        </div>
                        {result.speaker ? (
                          <p className="font-medium">{result.speaker}</p>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            No speaker name
                          </p>
                        )}
                      </div>

                      {/* AI Face Match */}
                      <div className="rounded-lg border border-border bg-card p-4 space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="space-y-1 flex-1">
                            <h5 className="text-sm font-medium">
                              AI Identification
                            </h5>
                            {(() => {
                              const { label, isPropagated, detail } =
                                getMpIdReasonLabel(result.mpIdReason);
                              return (
                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2">
                                    <Badge
                                      variant="outline"
                                      className={
                                        isPropagated
                                          ? "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20"
                                          : "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20"
                                      }
                                    >
                                      {label}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {detail}
                                    </span>
                                  </div>
                                  <p className="text-xs">
                                    <span className="text-muted-foreground">
                                      Propagation:{" "}
                                    </span>
                                    <span
                                      className={
                                        isPropagated
                                          ? "text-purple-600 dark:text-purple-400 font-medium"
                                          : "text-muted-foreground"
                                      }
                                    >
                                      {isPropagated ? "true" : "false"}
                                    </span>
                                  </p>
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                        {result.detectedMemberName ? (
                          <div className="space-y-1">
                            <p className="font-medium">
                              {result.detectedMemberName}
                            </p>
                            {result.detectedPartyName && (
                              <p className="text-sm text-muted-foreground">
                                {result.detectedPartyName}
                              </p>
                            )}
                            {result.detectedConstituencyName && (
                              <p className="text-sm text-muted-foreground">
                                {result.detectedConstituencyName}
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            No face match
                          </p>
                        )}
                      </div>

                      {/* Manual Assignment */}
                      <div className="rounded-lg border border-border bg-card p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <h5 className="text-sm font-medium">
                            Manually Assigned
                          </h5>
                          <Badge
                            variant="outline"
                            className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20"
                          >
                            Correct
                          </Badge>
                        </div>
                        {result.manuallyAssignedMemberName ? (
                          <div className="space-y-1">
                            <p className="font-medium">
                              {result.manuallyAssignedMemberName}
                            </p>
                            {result.manuallyAssignedPartyName && (
                              <p className="text-sm text-muted-foreground">
                                {result.manuallyAssignedPartyName}
                              </p>
                            )}
                            {result.manuallyAssignedConstituencyName && (
                              <p className="text-sm text-muted-foreground">
                                {result.manuallyAssignedConstituencyName}
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            No manual assignment
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* Refresh Button */}
      {results.length > 0 && (
        <div className="flex justify-center">
          <Button onClick={fetchResults} variant="outline">
            Refresh Results
          </Button>
        </div>
      )}
    </div>
  );
}
