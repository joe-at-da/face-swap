"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import Image from "next/image";
import NativeVideoPlayer from "@/components/ui/native-video-player";

interface VideoSectionProps {
  clipUrl: string | null;
  verticalClipUrl: string | null;
  thumbnailUrl: string | null;
  verticalThumbnailUrl: string | null;
  title: string;
  onDurationLoaded?: (duration: number) => void;
  activeTab: "horizontal" | "vertical";
}

export default function VideoSection({
  clipUrl,
  verticalClipUrl,
  thumbnailUrl,
  verticalThumbnailUrl,
  title,
  onDurationLoaded,
  activeTab
}: VideoSectionProps) {
  const [hasHorizontalError, setHasHorizontalError] = useState(false);
  const [hasVerticalError, setHasVerticalError] = useState(false);

  return (
    <div className="p-6">
      {activeTab === "horizontal" && (
        <div className="space-y-4">
          {clipUrl && !hasHorizontalError ? (
            <NativeVideoPlayer
              src={clipUrl}
              poster={thumbnailUrl}
              className="w-full aspect-video"
              onError={() => setHasHorizontalError(true)}
              onDurationLoaded={onDurationLoaded}
            />
          ) : (
            <div className="w-full aspect-video bg-muted rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto" />
                <p className="text-muted-foreground">
                  {hasHorizontalError ? "Failed to load video" : "Horizontal video not available"}
                </p>
                {thumbnailUrl && (
                  <Image
                    src={thumbnailUrl}
                    alt={title}
                    width={384}
                    height={128}
                    className="max-w-sm max-h-32 object-cover rounded mx-auto mt-4"
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "vertical" && (
        <div className="space-y-4">
          {verticalClipUrl && !hasVerticalError ? (
            <div className="flex justify-center">
              <NativeVideoPlayer
                src={verticalClipUrl}
                poster={verticalThumbnailUrl || thumbnailUrl}
                className="w-[300px] aspect-[9/16] max-w-full"
                onError={() => setHasVerticalError(true)}
                onDurationLoaded={onDurationLoaded}
              />
            </div>
          ) : (
            <div className="w-full h-[400px] bg-muted rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto" />
                <p className="text-muted-foreground">
                  {hasVerticalError ? "Failed to load vertical video" : "Vertical video not available"}
                </p>
                {(verticalThumbnailUrl || thumbnailUrl) && (
                  <Image
                    src={verticalThumbnailUrl || thumbnailUrl || ""}
                    alt={title}
                    width={384}
                    height={128}
                    className="max-w-sm max-h-32 object-cover rounded mx-auto mt-4"
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}