"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MonitorPlay, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/lib/formatFileSize";
import { useVideoSize } from "@/hooks/use-video-size";

interface ClipMetadataPanelProps {
  clip: {
    id: string;
    created_at: string;
    updated_at: string;
    status: string;
    duration: string | null;
    segments: Array<{
      start_timestamp: string;
      end_timestamp: string;
    }>;
    transcript: string | null;
    clip_url: string | null;
    vertical_clip_url: string | null;
    watermark_url: string | null;
    watermark_position: string | null;
    parliament_member_clips: {
      id: string;
      title?: string;
      session_name?: string | null;
      parliament_members: {
        display_name: string;
        party_name: string | null;
        party_abbreviation: string | null;
        constituency_name: string | null;
        member_id?: number;
        profile_image?: string | null;
      };
    };
  };
}

export function ClipMetadataPanel({ clip }: ClipMetadataPanelProps) {
  const [isClipDetailsOpen, setIsClipDetailsOpen] = useState(false);
  const { horizontalSizeBytes, verticalSizeBytes, isLoading: isSizeLoading } = useVideoSize(
    clip.clip_url,
    clip.vertical_clip_url
  );

  const formatTimestamp = (timestamp: string): string => {
    // Timestamp format from DB is "MM:SS.mmm" (e.g., "87:24.949")
    // We want to display it as "hours:min:sec" (e.g., "01:27:24")
    try {
      const [minSec] = timestamp.split(".");
      const [minutes, seconds] = minSec.split(":").map(Number);

      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;

      return `${hours.toString().padStart(2, "0")}:${remainingMinutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
    } catch {
      return timestamp;
    }
  };

  const formatDateOnly = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    }).format(date);
  };

  const formatDuration = (duration: string | null) => {
    if (!duration) return "Unknown";

    // Duration is in MM:SS.000 format
    const parts = duration.split(':');
    if (parts.length >= 2) {
      const minutes = parseInt(parts[0]);
      const seconds = parseInt(parts[1].split('.')[0]);

      if (minutes > 0) {
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ${seconds} second${seconds !== 1 ? 's' : ''}`;
      }
      return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    }

    return duration;
  };

  return (
    <div className="space-y-4">
      {/* Clip Details Section */}
      <Card className="overflow-hidden py-2">
        <CardContent className="px-4 py-2 space-y-3">
          {/* Title - Clickable to toggle */}
          <button
            onClick={() => setIsClipDetailsOpen(!isClipDetailsOpen)}
            className="w-full text-left"
          >
            <h2 className="text-lg font-sans font-bold text-foreground flex items-center gap-2">
              <div className="p-1 rounded bg-slate-200">
                <MonitorPlay className="h-4 w-4" />
              </div>
              Clip Details
              <ChevronDown
                className={cn(
                  "h-4 w-4 ml-auto transition-transform duration-200",
                  isClipDetailsOpen && "rotate-180"
                )}
              />
            </h2>
          </button>

          {/* Collapsible Content */}
          {isClipDetailsOpen && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-3 text-sm">
                <span className="font-normal text-foreground text-sm font-sans">Duration:</span>
                <span className="font-normal text-foreground text-sm font-sans ml-auto">{formatDuration(clip.duration)}</span>
              </div>

              {(clip.clip_url || clip.vertical_clip_url) && (
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-normal text-foreground text-sm font-sans">Video Size:</span>
                  <span className="font-normal text-foreground text-sm font-sans ml-auto">
                    {isSizeLoading ? (
                      <Skeleton className="h-4 w-16 inline-block" />
                    ) : (
                      <>
                        {clip.clip_url && clip.vertical_clip_url ? (
                          <span>
                            {formatFileSize(horizontalSizeBytes)} Horiz. / {formatFileSize(verticalSizeBytes)} Vert.
                          </span>
                        ) : clip.clip_url ? (
                          formatFileSize(horizontalSizeBytes)
                        ) : (
                          formatFileSize(verticalSizeBytes)
                        )}
                      </>
                    )}
                  </span>
                </div>
              )}

              <div className="flex items-center gap-3 text-sm">
                <span className="font-normal text-foreground text-sm font-sans">Date:</span>
                <span className="font-normal text-foreground text-sm font-sans ml-auto">{formatDateOnly(clip.created_at)}</span>
              </div>

              {clip.parliament_member_clips.session_name && (
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-normal text-foreground text-sm font-sans">Session:</span>
                  <span className="font-normal text-foreground text-sm font-sans ml-auto">{clip.parliament_member_clips.session_name}</span>
                </div>
              )}

              <div className="flex items-center gap-3 text-sm">
                <span className="font-normal text-foreground text-sm font-sans">Segments:</span>
                <span className="font-normal text-foreground text-sm font-sans ml-auto">
                  {clip.segments.length} {clip.segments.length !== 1 ? 's' : ''}
                </span>
              </div>

              {clip.segments.length > 0 && (
                <div className="pt-2">
                  <h3 className="font-semibold text-sm font-sans text-foreground mb-2">Timestamps</h3>
                  <div className="space-y-2">
                    {clip.segments.map((segment, index) => (
                      <div key={index} className="space-y-1">
                        {clip.segments.length > 1 && (
                          <span className="font-normal text-muted-foreground text-sm font-sans">
                            Segment {index + 1}:
                          </span>
                        )}
                        <div className="flex items-center gap-3 text-sm">
                          <span className="font-normal text-foreground text-sm font-sans">Start:</span>
                          <span className="font-normal text-foreground text-sm font-sans ml-auto text-right">{formatTimestamp(segment.start_timestamp)}</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <span className="font-normal text-foreground text-sm font-sans">End:</span>
                          <span className="font-normal text-foreground text-sm font-sans ml-auto text-right">{formatTimestamp(segment.end_timestamp)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2">
                <h3 className="font-semibold text-sm font-sans text-foreground mb-2">Updates</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-3 text-sm">
                    <span className="font-normal text-foreground text-sm font-sans">Created:</span>
                    <span className="font-normal text-foreground text-sm font-sans ml-auto text-right">{formatDateOnly(clip.created_at)}</span>
                  </div>

                  <div className="flex items-center gap-3 text-sm">
                    <span className="font-normal text-foreground text-sm font-sans">Updated:</span>
                    <span className="font-normal text-foreground text-sm font-sans ml-auto text-right">{formatDateOnly(clip.updated_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}