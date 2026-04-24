"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, Search, Video } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  SelectedMPData,
  SpeakerFace,
} from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface ConfirmSubmissionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedMP: SelectedMPData | null;
  selectedFaces: SpeakerFace[];
  isSubmitting: boolean;
  onConfirm: () => void;
  sessionDate: string | null;
}

const PARTY_COLORS: Record<string, string> = {
  Lab: "bg-red-500",
  Con: "bg-blue-500",
  SNP: "bg-yellow-500",
  LD: "bg-orange-500",
  Green: "bg-green-500",
  DUP: "bg-red-700",
  SF: "bg-green-700",
  PC: "bg-green-600",
  SDLP: "bg-green-500",
  Alliance: "bg-yellow-600",
};

export function ConfirmSubmissionDialog({
  open,
  onOpenChange,
  selectedMP,
  selectedFaces,
  isSubmitting,
  onConfirm,
  sessionDate,
}: ConfirmSubmissionDialogProps) {
  if (!selectedMP) return null;

  const partyColor =
    PARTY_COLORS[selectedMP.partyAbbreviation] || "bg-gray-500";
  const primaryPortrait = selectedMP.portraits.find((p) => p.isPrimary);
  const rawPortraitUrl =
    primaryPortrait?.imageUrl || selectedMP.portraits[0]?.imageUrl;

  // Extract original URL from proxy URL if it exists
  const getDirectImageUrl = (url: string | undefined): string | undefined => {
    if (!url) return undefined;
    // If it's a proxy URL, extract the original URL
    if (url.startsWith("/api/proxy-image?url=")) {
      try {
        const decodedUrl = decodeURIComponent(
          url.replace("/api/proxy-image?url=", "")
        );
        return decodedUrl;
      } catch {
        return url;
      }
    }
    // Return direct URL as-is
    return url;
  };

  const portraitUrl = getDirectImageUrl(rawPortraitUrl);

  const handleGoogleImageSearch = (e: React.MouseEvent) => {
    e.stopPropagation();
    const searchQuery = `${selectedMP.displayName} uk mp`;
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
      searchQuery
    )}&tbm=isch`;
    window.open(searchUrl, "_blank");
  };

  const handleParliamentLiveSearch = (e: React.MouseEvent) => {
    e.stopPropagation();

    // Format session date as DD/MM/YYYY (UK format) if available
    let startDate = "";
    let endDate = "";
    if (sessionDate) {
      try {
        // Parse ISO date string (YYYY-MM-DD) directly to avoid timezone issues
        const dateMatch = sessionDate.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (dateMatch) {
          const [, year, month, day] = dateMatch;
          const formattedDate = `${day}/${month}/${year}`;
          startDate = formattedDate;
          endDate = formattedDate;
        } else {
          // Fallback to Date parsing if format is different
          const date = new Date(sessionDate);
          if (!isNaN(date.getTime())) {
            const day = String(date.getDate()).padStart(2, "0");
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const year = date.getFullYear();
            const formattedDate = `${day}/${month}/${year}`;
            startDate = formattedDate;
            endDate = formattedDate;
          }
        }
      } catch (error) {
        console.error("Error formatting date:", error);
      }
    }

    // Build the ParliamentLive.tv search URL
    const memberName = `${selectedMP.displayName} MP`;
    const params = new URLSearchParams({
      Keywords: "",
      Member: memberName,
      MemberId: selectedMP.memberId.toString(),
      House: "",
      Business: "",
      ...(startDate && { Start: startDate }),
      ...(endDate && { End: endDate }),
    });

    const searchUrl = `https://www.parliamentlive.tv/Search?${params.toString()}`;
    window.open(searchUrl, "_blank");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Confirm MP Identification</DialogTitle>
          <DialogDescription>
            Review the details before submitting this identification
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Selected MP */}
          <div className="rounded-lg border border-border p-4">
            <p className="mb-3 text-sm font-medium text-muted-foreground">
              Selected MP:
            </p>
            <div className="space-y-3">
              {/* Portrait */}
              <div className="relative h-64 w-full overflow-hidden rounded-lg bg-muted">
                {portraitUrl ? (
                  <img
                    src={portraitUrl}
                    alt={selectedMP.displayName}
                    className="absolute inset-0 h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    No Image
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-lg font-semibold">
                    {selectedMP.displayName}
                  </p>
                  <div className="flex items-center gap-1">
                    {/* Google Image Search Button */}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={handleGoogleImageSearch}
                      className="h-7 w-7 flex-shrink-0"
                      title="Search Google Images"
                    >
                      <Search className="h-4 w-4" />
                    </Button>
                    {/* ParliamentLive.tv Search Button */}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={handleParliamentLiveSearch}
                      className="h-7 w-7 flex-shrink-0"
                      title="Search ParliamentLive.tv"
                    >
                      <Video className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={cn(partyColor, "text-sm text-white")}>
                    {selectedMP.partyAbbreviation}
                  </Badge>
                  {selectedMP.constituencyName && (
                    <Badge variant="outline" className="text-sm">
                      {selectedMP.constituencyName}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Selected Faces */}
          <div className="rounded-lg border border-border p-4">
            <p className="mb-3 text-sm font-medium text-muted-foreground">
              Selected Faces: {selectedFaces.length}
            </p>
            <div className="grid grid-cols-3 gap-2">
              {selectedFaces.map((face) => (
                <div
                  key={face.id}
                  className="relative aspect-square overflow-hidden rounded-lg bg-muted"
                >
                  <img
                    src={face.s3Url}
                    alt={`Face ${face.faceIndex + 1}`}
                    className="absolute inset-0 w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute left-2 top-2">
                    <Badge variant="secondary" className="text-sm">
                      {face.faceIndex + 1}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Info Message */}
          <div className="rounded-lg bg-primary/10 p-3">
            <p className="text-sm text-foreground">
              This will add {selectedFaces.length} portrait
              {selectedFaces.length !== 1 ? "s" : ""} to the database for{" "}
              <span className="font-semibold">{selectedMP.displayName}</span>.
              These portraits will be used to improve MP identification accuracy
              in future processing runs.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="button" onClick={onConfirm} disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Submitting...
              </>
            ) : (
              "Confirm & Submit"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
