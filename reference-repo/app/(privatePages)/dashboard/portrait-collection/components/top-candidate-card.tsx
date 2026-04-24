"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Check, Loader2, Search, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MPCandidate } from "@/app/(privatePages)/dashboard/portrait-collection/constants";

interface TopCandidateCardProps {
  candidate: MPCandidate;
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

export function TopCandidateCard({
  candidate,
  selectedMemberId,
  onSelect,
  sessionDate,
}: TopCandidateCardProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(false);

  const isSelected = selectedMemberId === candidate.memberId;
  const partyColor = PARTY_COLORS[candidate.partyAbbreviation] || "bg-gray-500";
  const primaryPortrait = candidate.portraits.find((p) => p.isPrimary);
  const portrait = primaryPortrait || candidate.portraits[0];

  const portraitUrl = useFallback ? portrait?.fallbackUrl : portrait?.imageUrl;

  useEffect(() => {
    setIsLoading(true);
    setUseFallback(false);
  }, [candidate.memberId]);

  const handleImageLoad = () => {
    setIsLoading(false);
  };

  const handleImageError = () => {
    if (portrait?.fallbackUrl && !useFallback) {
      setUseFallback(true);
      setIsLoading(true);
    } else {
      setIsLoading(false);
    }
  };

  const handleGoogleImageSearch = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent candidate selection when clicking search button
    const searchQuery = `${candidate.displayName} uk mp`;
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
      searchQuery
    )}&tbm=isch`;
    window.open(searchUrl, "_blank");
  };

  const handleParliamentLiveSearch = (e: React.MouseEvent) => {
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

  return (
    <Button
      type="button"
      variant="outline"
      onClick={() => onSelect(candidate.memberId)}
      className={cn(
        "h-auto w-full flex-col gap-4 p-4 text-left transition-all hover:scale-[1.02]",
        isSelected && "border-primary bg-primary/5 shadow-md"
      )}
    >
      {/* Large Portrait */}
      <div className="relative h-64 w-full overflow-hidden rounded-lg bg-muted">
        {/* Loading Spinner */}
        {isLoading && portraitUrl && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {portraitUrl ? (
          <Image
            key={`${candidate.memberId}-${
              useFallback ? "fallback" : "primary"
            }`}
            src={portraitUrl}
            alt={candidate.displayName}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 400px"
            onLoad={handleImageLoad}
            onError={handleImageError}
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
}
