"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Check, Loader2, Search, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MPCandidate } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface MpCandidatesListProps {
  candidates: MPCandidate[];
  selectedMemberId: number | null;
  onSelect: (memberId: number) => void;
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

export function MpCandidatesList({
  candidates,
  selectedMemberId,
  onSelect,
  sessionDate,
}: MpCandidatesListProps) {
  // Track loading and fallback states for each candidate's portrait
  const [loadingStates, setLoadingStates] = useState<Record<number, boolean>>(
    () => {
      const initial: Record<number, boolean> = {};
      candidates.forEach((candidate) => {
        initial[candidate.memberId] = true;
      });
      return initial;
    }
  );

  const [fallbackStates, setFallbackStates] = useState<Record<number, boolean>>(
    {}
  );

  // Reset states when candidates change (new segment loaded)
  useEffect(() => {
    const newLoadingStates: Record<number, boolean> = {};
    candidates.forEach((candidate) => {
      newLoadingStates[candidate.memberId] = true;
    });
    setLoadingStates(newLoadingStates);
    setFallbackStates({});
  }, [candidates]);

  const handleImageLoad = (memberId: number) => {
    setLoadingStates((prev) => ({ ...prev, [memberId]: false }));
  };

  const handleImageError = (memberId: number, candidate: MPCandidate) => {
    setLoadingStates((prev) => ({ ...prev, [memberId]: false }));
    // If there's a fallback URL and we haven't tried it yet, use it
    const primaryPortrait = candidate.portraits.find((p) => p.isPrimary);
    const portrait = primaryPortrait || candidate.portraits[0];
    if (portrait?.fallbackUrl && !fallbackStates[memberId]) {
      setFallbackStates((prev) => ({ ...prev, [memberId]: true }));
      setLoadingStates((prev) => ({ ...prev, [memberId]: true }));
    }
  };

  const handleGoogleImageSearch = (
    e: React.MouseEvent,
    candidate: MPCandidate
  ) => {
    e.stopPropagation(); // Prevent candidate selection when clicking search button
    const searchQuery = `${candidate.displayName} uk mp`;
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
      searchQuery
    )}&tbm=isch`;
    window.open(searchUrl, "_blank");
  };

  const handleParliamentLiveSearch = (
    e: React.MouseEvent,
    candidate: MPCandidate
  ) => {
    e.stopPropagation(); // Prevent candidate selection when clicking search button

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
    const memberName = `${candidate.displayName} MP`;
    const params = new URLSearchParams({
      Keywords: "",
      Member: memberName,
      MemberId: candidate.memberId.toString(),
      House: "",
      Business: "",
      ...(startDate && { Start: startDate }),
      ...(endDate && { End: endDate }),
    });

    const searchUrl = `https://www.parliamentlive.tv/Search?${params.toString()}`;
    window.open(searchUrl, "_blank");
  };

  if (candidates.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-muted/50 p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No candidate matches found for this segment
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Top {candidates.length} candidate{candidates.length !== 1 ? "s" : ""}{" "}
        (sorted by similarity)
      </p>
      <div className="grid grid-cols-2 gap-4">
        {candidates.map((candidate) => {
          const isSelected = selectedMemberId === candidate.memberId;
          const partyColor =
            PARTY_COLORS[candidate.partyAbbreviation] || "bg-gray-500";
          const primaryPortrait = candidate.portraits.find((p) => p.isPrimary);
          const portrait = primaryPortrait || candidate.portraits[0];

          // Determine which URL to use based on fallback state
          const portraitUrl = fallbackStates[candidate.memberId]
            ? portrait?.fallbackUrl
            : portrait?.imageUrl;

          return (
            <Button
              key={candidate.memberId}
              type="button"
              variant="outline"
              onClick={() => onSelect(candidate.memberId)}
              className={cn(
                "h-auto w-full flex-col gap-3 p-4 text-left transition-all hover:scale-[1.02]",
                isSelected && "border-primary bg-primary/5 shadow-md"
              )}
            >
              {/* Portrait */}
              <div className="relative h-48 w-full overflow-hidden rounded-lg bg-muted">
                {/* Loading Spinner */}
                {loadingStates[candidate.memberId] && portraitUrl && (
                  <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                )}

                {portraitUrl ? (
                  <Image
                    key={`${candidate.memberId}-${
                      fallbackStates[candidate.memberId]
                        ? "fallback"
                        : "primary"
                    }`}
                    src={portraitUrl}
                    alt={candidate.displayName}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, 400px"
                    onLoad={() => handleImageLoad(candidate.memberId)}
                    onError={() =>
                      handleImageError(candidate.memberId, candidate)
                    }
                    unoptimized
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    No Image
                  </div>
                )}

                {/* Selection Indicator */}
                {isSelected && (
                  <div className="absolute inset-0 flex items-center justify-center bg-primary/30">
                    <div className="rounded-full bg-primary p-3">
                      <Check className="h-6 w-6 text-primary-foreground" />
                    </div>
                  </div>
                )}

                {/* Similarity Badge */}
                <div className="absolute right-3 top-3">
                  <Badge
                    variant="secondary"
                    className="bg-background/90 text-sm font-semibold"
                  >
                    {Math.round(candidate.similarity * 100)}% match
                  </Badge>
                </div>
              </div>

              {/* Info */}
              <div className="w-full space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-lg font-semibold leading-tight">
                    {candidate.displayName}
                  </p>
                  <div className="flex items-center gap-1">
                    {/* Google Image Search Button */}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleGoogleImageSearch(e, candidate)}
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
                      onClick={(e) => handleParliamentLiveSearch(e, candidate)}
                      className="h-7 w-7 flex-shrink-0"
                      title="Search ParliamentLive.tv"
                    >
                      <Video className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={cn(partyColor, "text-sm text-white")}>
                    {candidate.partyAbbreviation}
                  </Badge>
                  {candidate.constituencyName && (
                    <Badge variant="outline" className="text-sm">
                      {candidate.constituencyName}
                    </Badge>
                  )}
                </div>
              </div>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
