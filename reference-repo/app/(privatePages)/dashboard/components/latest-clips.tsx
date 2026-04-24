import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MonitorPlay, Calendar, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { formatDuration } from "@/lib/formatDuration";
import { getDisplayTranscript } from "@/lib/fixTranscriptCapitalization";

interface ParliamentMemberClip {
  id: string;
  created_at: string | null;
  session_date: string | null;
  session_uid: string | null;
  transcript: string | null;
  transcript_manually_edited: boolean;
  description: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  parliament_event?: {
    session_date: string | null;
    title: string | null;
  } | null;
}

interface LatestClipsProps {
  clips: ParliamentMemberClip[];
  mpName: string;
}

export function LatestClips({ clips, mpName }: LatestClipsProps) {
  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "Unknown date";
    try {
      return format(new Date(dateStr), "MMM d, yyyy");
    } catch {
      return "Unknown date";
    }
  };

  const getThumbnailUrl = (clip: ParliamentMemberClip) => {
    return (
      clip.thumbnail_url ||
      "data:image/svg+xml,%3csvg width='320' height='180' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='100%25' height='100%25' fill='%23f1f5f9'/%3e%3ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280' font-family='system-ui' font-size='14'%3eNo thumbnail%3c/text%3e%3c/svg%3e"
    );
  };

  const getSessionDate = (clip: ParliamentMemberClip): string => {
    return (
      clip.parliament_event?.session_date ||
      clip.session_date ||
      clip.created_at ||
      ""
    );
  };

  const truncateText = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + "...";
  };

  if (clips.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Latest Clips</h2>
        </div>
        <Card className="p-8">
          <div className="text-center space-y-4">
            <div className="mx-auto w-12 h-12 bg-slate-200 rounded flex items-center justify-center">
              <MonitorPlay className="h-8 w-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-bold">No clips available yet</h3>
              <p className="text-muted-foreground text-sm">
                {mpName
                  ? `No recent speeches available for ${mpName}.`
                  : "Follow an MP to see their latest speeches."}
              </p>
            </div>
            <Button asChild>
              <Link href="/dashboard/create-clips">Go to Speech Library</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">Latest Clips</h2>
        <Button variant="ghost" asChild>
          <Link href="/dashboard/create-clips" className="flex items-center gap-2">
            View all clips
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {clips.map((clip) => {
          const sessionDate = getSessionDate(clip);
          const sessionTitle = clip.parliament_event?.title;
          const description = clip.description?.trim() || null;

          return (
            <Link
              key={clip.id}
              href={`/dashboard/create-clips/clip/${clip.id}`}
            >
              <Card className="group hover:shadow-md transition-all duration-200 cursor-pointer p-0">
                <CardContent className="p-0">
                  {/* Video Preview */}
                  <div className="relative aspect-video bg-muted rounded-t-lg overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={getThumbnailUrl(clip)}
                      alt="Clip thumbnail"
                      className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    />

                    {/* Duration badge */}
                    {clip.duration_seconds && (
                      <div className="absolute bottom-2 right-2 bg-white text-foreground px-2 py-1 rounded text-sm md:text-xs font-medium">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {formatDuration(clip.duration_seconds)}
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="p-4 space-y-3">
                    {/* Session info */}
                    <div className="flex items-center justify-between text-sm md:text-xs text-muted-foreground pt-2">
                      {sessionTitle && (
                        <p className="text-xs truncate flex-1 mr-2">{sessionTitle}</p>
                      )}
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Calendar className="h-4 w-4 md:h-3 md:w-3" />
                        <span>{formatDate(sessionDate)}</span>
                      </div>
                    </div>

                    {/* Description or Transcript */}
                    <div className="space-y-2">
                      <p className="text-base md:text-sm text-foreground line-clamp-3 leading-relaxed">
                        {description || truncateText(getDisplayTranscript(clip.transcript, clip.transcript_manually_edited) || "", 150)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
