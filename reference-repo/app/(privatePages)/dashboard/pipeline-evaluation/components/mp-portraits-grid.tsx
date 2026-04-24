"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Loader2, Star, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MPPortrait } from "../constants";

interface MPPortraitsGridProps {
  portraits: MPPortrait[];
  memberName: string | null;
  partyName: string | null;
  constituencyName: string | null;
}

export function MPPortraitsGrid({
  portraits,
  memberName,
  partyName,
  constituencyName,
}: MPPortraitsGridProps) {
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    () => {
      const initial: Record<string, boolean> = {};
      portraits.forEach((portrait) => {
        initial[portrait.id] = true;
      });
      return initial;
    }
  );

  // Track which portraits are using fallback URLs
  const [fallbackStates, setFallbackStates] = useState<Record<string, boolean>>(
    {}
  );

  // Reset states when portraits change (new segment loaded)
  useEffect(() => {
    const newLoadingStates: Record<string, boolean> = {};
    portraits.forEach((portrait) => {
      newLoadingStates[portrait.id] = true;
    });
    setLoadingStates(newLoadingStates);
    setFallbackStates({});
  }, [portraits]);

  const handleImageLoad = (id: string) => {
    setLoadingStates((prev) => ({ ...prev, [id]: false }));
  };

  const handleImageError = (id: string, portrait: MPPortrait) => {
    setLoadingStates((prev) => ({ ...prev, [id]: false }));
    // If there's a fallback URL and we haven't tried it yet, use it
    if (portrait.fallbackUrl && !fallbackStates[id]) {
      setFallbackStates((prev) => ({ ...prev, [id]: true }));
      setLoadingStates((prev) => ({ ...prev, [id]: true }));
    }
  };

  const handleGoogleImageSearch = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!memberName) return;
    const searchQuery = `${memberName} UK MP`;
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(
      searchQuery
    )}&tbm=isch`;
    window.open(searchUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="space-y-3">
      {/* MP Info */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-foreground font-serif">
            {memberName || "Unknown MP"}
          </h3>
          {memberName && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={handleGoogleImageSearch}
              title={`Search Google Images for "${memberName} UK MP"`}
            >
              <Search className="h-4 w-4" />
            </Button>
          )}
        </div>
        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
          {partyName && (
            <span className="px-2 py-0.5 bg-muted rounded-full">
              {partyName}
            </span>
          )}
          {constituencyName && <span>{constituencyName}</span>}
        </div>
      </div>

      {/* Portraits Grid */}
      {portraits.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground border border-dashed border-border rounded-lg">
          <p className="text-sm">No portraits available for this MP</p>
        </div>
      ) : (
        <>
          <p className="text-sm font-medium text-foreground">
            MP Portraits ({portraits.length})
          </p>
          <div className="grid grid-cols-2 gap-3">
            {portraits.map((portrait) => (
              <div
                key={portrait.id}
                className={`relative aspect-square rounded-lg overflow-hidden border bg-muted ${
                  portrait.isPrimary
                    ? "border-primary border-2"
                    : "border-border"
                }`}
              >
                {loadingStates[portrait.id] && (
                  <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                )}
                <Image
                  key={`${portrait.id}-${
                    fallbackStates[portrait.id] ? "fallback" : "primary"
                  }`}
                  src={
                    fallbackStates[portrait.id] && portrait.fallbackUrl
                      ? portrait.fallbackUrl
                      : portrait.imageUrl
                  }
                  alt={`${memberName || "MP"} portrait`}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 50vw, 25vw"
                  onLoad={() => handleImageLoad(portrait.id)}
                  onError={() => handleImageError(portrait.id, portrait)}
                  unoptimized // Disable Next.js image optimization to prevent retries
                  loading="lazy" // Lazy load images to reduce initial load
                />
                {portrait.isPrimary && (
                  <div className="absolute top-1 right-1 bg-primary text-primary-foreground p-1 rounded-full">
                    <Star className="h-3 w-3 fill-current" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
