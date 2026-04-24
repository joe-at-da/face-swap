"use client";

import { useState, forwardRef, useImperativeHandle, useRef } from "react";
import { Button } from "@/components/ui/button";
import { MpInfoHorizontal } from "./mp-info-horizontal";

interface PublicClipViewerProps {
  clipUrl: string | null;
  verticalClipUrl: string | null;
  thumbnailUrl: string | null;
  verticalThumbnailUrl: string | null;
  duration: string | null;
  mpName?: string;
  constituency?: string | null;
  profileImage?: string | null;
}

export interface PublicClipViewerRef {
  getCurrentVideoUrl: () => string | null;
  getSelectedFormat: () => "horizontal" | "vertical";
}

export const PublicClipViewer = forwardRef<PublicClipViewerRef, PublicClipViewerProps>(
  (
    {
      clipUrl,
      verticalClipUrl,
      thumbnailUrl,
      verticalThumbnailUrl,
      mpName,
      constituency,
      profileImage,
    },
    ref
  ) => {
    const [selectedFormat, setSelectedFormat] = useState<
      "horizontal" | "vertical"
    >("horizontal");
    const videoRef = useRef<HTMLVideoElement>(null);

    const currentVideoUrl =
      selectedFormat === "horizontal" ? clipUrl : verticalClipUrl;
    const currentThumbnail =
      selectedFormat === "horizontal" ? thumbnailUrl : verticalThumbnailUrl;

    const hasHorizontal = Boolean(clipUrl);
    const hasVertical = Boolean(verticalClipUrl);

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      getCurrentVideoUrl: () => currentVideoUrl,
      getSelectedFormat: () => selectedFormat,
    }));

    if (!hasHorizontal && !hasVertical) {
      return (
        <div className="flex items-center justify-center h-96 bg-slate-100 rounded-lg">
          <p className="text-muted-foreground">Video not available</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {/* Format Toggle */}
        {hasHorizontal && hasVertical && (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex gap-2">
              <Button
                variant={selectedFormat === "horizontal" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedFormat("horizontal")}
              >
                Landscape (16:9)
              </Button>
              <Button
                variant={selectedFormat === "vertical" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedFormat("vertical")}
              >
                Portrait (9:16)
              </Button>
            </div>
            {/* Horizontal MP Info - Mobile only */}
            {mpName && (
              <MpInfoHorizontal
                mpName={mpName}
                constituency={constituency || null}
                profileImage={profileImage || null}
                isMP={true}
              />
            )}
          </div>
        )}

        {/* Horizontal MP Info - Mobile only (when format selector is not shown) */}
        {!(hasHorizontal && hasVertical) && mpName && (
          <div className="lg:hidden">
            <MpInfoHorizontal
              mpName={mpName}
              constituency={constituency || null}
              profileImage={profileImage || null}
              isMP={true}
            />
          </div>
        )}

        {/* Video Player */}
        <div className="relative bg-slate-900 rounded-lg overflow-hidden aspect-video">
          <video
            ref={videoRef}
            controls
            className="w-full h-full"
            poster={currentThumbnail || undefined}
            key={currentVideoUrl}
          >
            <source src={currentVideoUrl || ""} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>

        {/* Video Source Credit */}
        <div className="flex justify-end mt-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted border border-border">
            <span className="text-xs text-muted-foreground">
              Source: parliamentlive.tv
            </span>
          </div>
        </div>
      </div>
    );
  }
);

PublicClipViewer.displayName = "PublicClipViewer";
