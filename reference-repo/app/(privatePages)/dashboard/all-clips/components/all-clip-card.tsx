"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, Calendar } from "lucide-react";
import { format } from "date-fns";
import { formatDuration } from "@/lib/formatDuration";
import PreviewVideo from "@/app/(privatePages)/dashboard/create-clips/components/preview-video";
import { SmartAvatar } from "@/components/smart-avatar";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";
import type { AllClipWithMP } from "@/types/parliament";

interface AllClipCardProps {
  clip: AllClipWithMP;
  teamId?: string;
  from?: string;
}

export default function AllClipCard({ clip, teamId, from }: AllClipCardProps) {
  const router = useRouter();
  const [actualDuration, setActualDuration] = useState<number | null>(null);

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "Unknown date";
    try {
      return format(new Date(dateStr), "MMM d, yyyy");
    } catch {
      return "Unknown date";
    }
  };

  const handleClick = () => {
    const params = new URLSearchParams();
    if (teamId) params.set("teamId", teamId);
    if (from) params.set("from", from);
    const qs = params.toString();
    router.push(`/dashboard/create-clips/clip/${clip.id}${qs ? `?${qs}` : ""}`);
  };

  const displayText =
    clip.description?.trim() ||
    getDisplayTranscript(clip.transcript, clip.transcript_manually_edited);

  return (
    <Card
      className="group hover:shadow-md transition-all duration-200 cursor-pointer p-0"
      onClick={handleClick}
    >
      <CardContent className="p-0">
        {/* Video Preview */}
        <div className="relative aspect-video bg-muted rounded-t-lg overflow-hidden">
          <PreviewVideo
            src={clip.clip_url}
            poster={clip.thumbnail_url}
            onClick={handleClick}
            onDurationLoaded={setActualDuration}
          />
          <div className="absolute bottom-2 right-2 bg-foreground/70 text-primary-foreground px-2 py-1 rounded text-sm md:text-xs font-medium">
            <Clock className="h-3 w-3 inline mr-1" />
            {formatDuration(actualDuration ?? clip.duration_seconds)}
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* MP info row */}
          <div className="flex items-center gap-2">
            <SmartAvatar
              profileImage={clip.mp_portrait_url}
              firstName={clip.mp_display_name?.split(" ")[0]}
              lastName={clip.mp_display_name?.split(" ").slice(1).join(" ")}
              className="h-6 w-6"
            />
            <span className="text-sm font-medium truncate">
              {clip.mp_display_name || "Unknown MP"}
            </span>
            {clip.mp_party_abbreviation && (
              <Badge
                variant="outline"
                className="shrink-0 text-[10px] px-1.5 py-0"
                style={{
                  backgroundColor: clip.mp_party_background_colour
                    ? `#${clip.mp_party_background_colour}20`
                    : undefined,
                  borderColor: clip.mp_party_background_colour
                    ? `#${clip.mp_party_background_colour}`
                    : undefined,
                }}
              >
                {clip.mp_party_abbreviation}
              </Badge>
            )}
          </div>

          {/* Session info */}
          <div className="flex items-center justify-between text-sm md:text-xs text-muted-foreground">
            {clip.parliament_event?.title && (
              <p className="text-xs text-muted-foreground truncate">
                {clip.parliament_event.title}
              </p>
            )}
            <div className="flex items-center gap-1 shrink-0">
              <Calendar className="h-3 w-3" />
              <span>
                {clip.parliament_event?.session_date
                  ? formatDate(clip.parliament_event.session_date)
                  : clip.session_date
                    ? formatDate(clip.session_date)
                    : formatDate(clip.created_at)}
              </span>
            </div>
          </div>

          {/* Description/Transcript */}
          <p className="text-sm text-foreground line-clamp-3 leading-relaxed">
            {displayText}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
