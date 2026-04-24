"use client";

import { useState } from "react";
import { usePostHog } from "posthog-js/react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Download,
  Loader2,
  RectangleHorizontal,
  RectangleVertical
} from "lucide-react";

interface ClipDownloadSectionProps {
  clip_url: string | null;
  vertical_clip_url: string | null;
  clipId?: string;
}

export function ClipDownloadSection({ clip_url, vertical_clip_url, clipId }: ClipDownloadSectionProps) {
  const posthog = usePostHog();
  const [downloadingFormat, setDownloadingFormat] = useState<'horizontal' | 'vertical' | null>(null);

  const handleDownload = async (url: string, format: 'horizontal' | 'vertical') => {
    if (!url) return;

    try {
      setDownloadingFormat(format);

      // Fetch the video as a blob to bypass CORS restrictions
      const response = await fetch(url);
      const blob = await response.blob();

      // Create a blob URL
      const blobUrl = URL.createObjectURL(blob);

      // Create a temporary anchor element and trigger download
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `clip-${format}-${Date.now()}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      // Clean up the blob URL
      URL.revokeObjectURL(blobUrl);

      // Track successful download
      posthog.capture("clip_downloaded", {
        clip_id: clipId,
        source: "dashboard_my_clips",
        format: format,
      });
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="group relative overflow-hidden p-4 transition-all duration-300">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="bg-slate-200 rounded p-1">
                  <Download className="h-4 w-4 text-primary" />
                </div>
                <span className="text-lg font-sans font-bold">Download</span>
              </div>
              <p className="text-base font-sans font-normal text-muted-foreground">
                {clip_url || vertical_clip_url
                  ? "Horizontal 16:9 | Vertical 9:16"
                  : "Not available"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => clip_url && handleDownload(clip_url, 'horizontal')}
              disabled={!clip_url || downloadingFormat === 'horizontal'}
              size="lg"
              className="flex-1 gap-2 transition-all"
            >
              {downloadingFormat === 'horizontal' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Downloading...</span>
                </>
              ) : (
                <>
                  <RectangleHorizontal className="h-4 w-4" />
                  <span>Horizontal</span>
                </>
              )}
            </Button>
            <Button
              onClick={() => vertical_clip_url && handleDownload(vertical_clip_url, 'vertical')}
              disabled={!vertical_clip_url || downloadingFormat === 'vertical'}
              size="lg"
              className="flex-1 gap-2 transition-all"
            >
              {downloadingFormat === 'vertical' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Downloading...</span>
                </>
              ) : (
                <>
                  <RectangleVertical className="h-4 w-4" />
                  <span>Vertical</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
