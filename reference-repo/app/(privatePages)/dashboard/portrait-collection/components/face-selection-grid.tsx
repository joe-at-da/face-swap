"use client";

import { useState } from "react";
import { Check, Loader2, Search, Sparkles, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { SpeakerFace } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface FaceSelectionGridProps {
  faces: SpeakerFace[];
  selectedIndices: Set<number>;
  onToggle: (faceIndex: number) => void;
  onMpSelect: (memberId: number) => void;
}

interface AIResult {
  detected: boolean;
  mpName: string | null;
  memberId: number | null;
  confidence: "high" | "medium" | "low" | null;
  matchedMember?: {
    member_id: number;
    display_name: string;
    party_abbreviation: string;
    constituency_name: string | null;
  } | null;
}

export function FaceSelectionGrid({
  faces,
  selectedIndices,
  onToggle,
  onMpSelect,
}: FaceSelectionGridProps) {
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    {}
  );
  const [errorStates, setErrorStates] = useState<Record<string, boolean>>({});
  const [aiIdentifying, setAiIdentifying] = useState<string | null>(null);
  const [aiResult, setAiResult] = useState<AIResult | null>(null);
  const [showAiDialog, setShowAiDialog] = useState(false);
  const [hasClickedVerification, setHasClickedVerification] = useState(false);

  const handleReverseImageSearch = (face: SpeakerFace, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent face selection when clicking search button

    // Open Google Lens reverse image search in new tab with "uk mp" context
    const searchUrl = `https://lens.google.com/uploadbyurl?url=${encodeURIComponent(
      face.s3Url
    )}&text=${encodeURIComponent("uk mp")}`;
    window.open(searchUrl, "_blank");
  };

  const handleAIIdentification = async (
    face: SpeakerFace,
    e: React.MouseEvent
  ) => {
    e.stopPropagation(); // Prevent face selection when clicking AI button

    setAiIdentifying(face.id);
    setAiResult(null);
    setHasClickedVerification(false); // Reset verification state

    try {
      const response = await fetch(
        "/api/portrait-collection/identify-with-ai",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ imageUrl: face.s3Url }),
        }
      );

      if (!response.ok) {
        throw new Error("AI identification failed");
      }

      const result = await response.json();
      setAiResult(result);
      setShowAiDialog(true);
    } catch (error) {
      console.error("AI identification error:", error);
      setAiResult({
        detected: false,
        mpName: null,
        memberId: null,
        confidence: null,
      });
      setShowAiDialog(true);
    } finally {
      setAiIdentifying(null);
    }
  };

  const handleSelectMP = () => {
    if (aiResult?.matchedMember) {
      onMpSelect(aiResult.matchedMember.member_id);
      setShowAiDialog(false);
      setHasClickedVerification(false); // Reset for next time
    }
  };

  const handleCloseDialog = () => {
    setShowAiDialog(false);
    setHasClickedVerification(false); // Reset for next time
  };

  if (faces.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted/50 p-8 text-center">
        <p className="text-sm text-muted-foreground">No faces detected</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        {faces.map((face) => {
          const isSelected = selectedIndices.has(face.faceIndex);
          const isLoading = loadingStates[face.id];
          const hasError = errorStates[face.id];

          return (
            <div
              key={face.id}
              onClick={() => onToggle(face.faceIndex)}
              className={cn(
                "group relative aspect-square overflow-hidden rounded-lg border-2 transition-all hover:scale-105 cursor-pointer",
                isSelected
                  ? "border-primary shadow-lg"
                  : "border-border hover:border-primary/50"
              )}
            >
              {/* Image */}
              <div className="relative h-full w-full bg-muted">
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
                    alt={`Speaker face ${face.faceIndex + 1}`}
                    className="absolute inset-0 w-full h-full object-cover"
                    loading="lazy"
                    onLoad={() => {
                      setLoadingStates((prev) => ({
                        ...prev,
                        [face.id]: false,
                      }));
                      setErrorStates((prev) => ({ ...prev, [face.id]: false }));
                    }}
                    onError={() => {
                      setLoadingStates((prev) => ({
                        ...prev,
                        [face.id]: false,
                      }));
                      setErrorStates((prev) => ({ ...prev, [face.id]: true }));
                    }}
                  />
                )}

                {/* Selection Overlay */}
                {isSelected && (
                  <div className="absolute inset-0 bg-primary/20 backdrop-blur-[1px]">
                    <div className="flex h-full items-center justify-center">
                      <div className="rounded-full bg-primary p-2">
                        <Check className="h-6 w-6 text-primary-foreground" />
                      </div>
                    </div>
                  </div>
                )}

                {/* Face Index Badge */}
                <div className="absolute left-2 top-2">
                  <Badge variant="secondary" className="text-xs">
                    Face {face.faceIndex + 1}
                  </Badge>
                </div>

                {/* Quality Score Badge */}
                {face.qualityScore !== null && (
                  <div className="absolute right-2 top-2">
                    <Badge
                      variant="outline"
                      className="bg-background/80 text-xs"
                    >
                      {Math.round(face.qualityScore * 100)}% quality
                    </Badge>
                  </div>
                )}

                {/* Frontal Badge */}
                {face.isFrontal && (
                  <div className="absolute bottom-2 left-2">
                    <Badge
                      variant="outline"
                      className="bg-background/80 text-xs"
                    >
                      Frontal
                    </Badge>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="absolute bottom-2 right-2 flex gap-1">
                  {/* AI Identification Button */}
                  <Button
                    type="button"
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8 rounded-full bg-background/90 hover:bg-background"
                    onClick={(e) => handleAIIdentification(face, e)}
                    disabled={aiIdentifying === face.id}
                    title="Identify MP with AI"
                  >
                    {aiIdentifying === face.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                  </Button>

                  {/* Reverse Image Search Button */}
                  <Button
                    type="button"
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8 rounded-full bg-background/90 hover:bg-background"
                    onClick={(e) => handleReverseImageSearch(face, e)}
                    title="Search UK MPs with Google Lens"
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* AI Results Dialog */}
      <Dialog open={showAiDialog} onOpenChange={handleCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>AI MP Identification</DialogTitle>
            <DialogDescription>
              Results from AI-powered MP identification
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {aiResult?.detected ? (
              <div className="space-y-3">
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <div className="space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold text-lg">
                          {aiResult.matchedMember?.display_name ||
                            aiResult.mpName}
                        </p>
                        {aiResult.matchedMember && (
                          <div className="mt-1 flex gap-2 text-sm text-muted-foreground">
                            <span>
                              {aiResult.matchedMember.party_abbreviation}
                            </span>
                            {aiResult.matchedMember.constituency_name && (
                              <>
                                <span>•</span>
                                <span>
                                  {aiResult.matchedMember.constituency_name}
                                </span>
                              </>
                            )}
                          </div>
                        )}
                        {aiResult.memberId && (
                          <p className="mt-1 text-sm text-muted-foreground">
                            Member ID: {aiResult.memberId}
                          </p>
                        )}
                      </div>
                      {aiResult.confidence && (
                        <Badge
                          variant={
                            aiResult.confidence === "high"
                              ? "default"
                              : aiResult.confidence === "medium"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {aiResult.confidence} confidence
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                {/* Google Image Search for Verification */}
                {aiResult.mpName && !hasClickedVerification && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Verify this identification:
                    </p>
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => {
                        const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
                          `${aiResult.mpName} UK MP`
                        )}&tbm=isch`;
                        window.open(searchUrl, "_blank");
                        setHasClickedVerification(true);
                      }}
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Search Google Images for &quot;{aiResult.mpName}&quot;
                    </Button>
                  </div>
                )}

                {/* Action buttons after verification */}
                {hasClickedVerification && aiResult.matchedMember && (
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={handleCloseDialog}
                    >
                      Cancel
                    </Button>
                    <Button className="flex-1" onClick={handleSelectMP}>
                      Select this MP
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-muted/50 p-8 text-center">
                <p className="text-muted-foreground">
                  AI could not detect or identify an MP in this image.
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Try using the manual search or reverse image search instead.
                </p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
