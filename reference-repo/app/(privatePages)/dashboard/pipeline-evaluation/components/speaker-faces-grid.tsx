"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import type { SpeakerFace } from "../constants";

interface SpeakerFacesGridProps {
  faces: SpeakerFace[];
}

export function SpeakerFacesGrid({ faces }: SpeakerFacesGridProps) {
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

  // Reset loading states when faces change (new segment loaded)
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
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No speaker faces detected for this segment</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">
        Detected Speaker Faces ({faces.length})
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {faces.map((face) => {
          const isLoading = loadingStates[face.id];
          const hasError = errorStates[face.id];

          return (
            <div
              key={face.id}
              className="relative aspect-square rounded-lg overflow-hidden border border-border bg-muted"
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
                  alt={`Speaker face ${face.faceIndex + 1}`}
                  className="absolute inset-0 w-full h-full object-cover"
                  loading="lazy"
                  onLoad={() => handleImageLoad(face.id)}
                  onError={() => handleImageError(face.id)}
                />
              )}
              {face.qualityScore !== null && !hasError && (
                <div className="absolute bottom-1 right-1 bg-background/80 backdrop-blur-sm px-1.5 py-0.5 rounded text-xs font-medium">
                  {Math.round(face.qualityScore * 100)}%
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
