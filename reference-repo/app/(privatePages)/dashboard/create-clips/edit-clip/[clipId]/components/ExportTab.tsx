"use client";

import React, { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { observer } from "@legendapp/state/react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Download,
  Loader2,
  Monitor,
  Maximize2,
  Clock,
  Film,
  Type,
  Captions,
  ImageIcon,
  Info,
} from "lucide-react";
import { editor$, getCompositionJSON, resetEditor } from "@/stores/editorStore";
import { subtitle$, DEFAULT_STYLE, resetSubtitleStore } from "@/stores/subtitleStore";
import { resetPlayerStore } from "@/stores/remotionPlayerStore";
import { videoCompositionSchema } from "@/schemas/compositionSchema";
import { toast } from "sonner";
import { ErrorLogger } from "@/lib/errorLogger";
import { EDITOR_FPS } from "@/lib/editorConstants";

function SummaryRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        {label}
      </span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function ExportTabInner() {
  const totalDurationInFrames = editor$.totalDurationInFrames.get();
  const tracks = editor$.tracks.get();
  const clipId = editor$.clipId.get();
  const teamId = editor$.teamId.get();

  const router = useRouter();
  const [exporting, setExporting] = useState(false);

  const videoItemCount = tracks
    .flatMap((t) => t.items)
    .filter((i) => i.type === "video").length;
  const textItemCount = tracks
    .flatMap((t) => t.items)
    .filter((i) => i.type === "text").length;
  const durationSeconds = (totalDurationInFrames / EDITOR_FPS).toFixed(1);

  const imageItemCount = tracks
    .flatMap((t) => t.items)
    .filter((i) => i.type === "image").length;

  // Check for subtitles presence
  const captionsByItemId = subtitle$.captionsByItemId.get();
  const hasSubtitles = Object.values(captionsByItemId).some(
    (caps) => caps && caps.length > 0
  );

  const handleExport = useCallback(async () => {
    if (!clipId) {
      toast.error("No clip loaded");
      return;
    }

    if (totalDurationInFrames === 0) {
      toast.error("Timeline is empty");
      return;
    }

    setExporting(true);

    try {
      // Build subtitle track from store (export uses per-item styles, first item's or default)
      const captionsSnapshot = subtitle$.captionsByItemId.peek();
      const stylesSnapshot = subtitle$.styleByItemId.peek();
      const editorTracks = editor$.tracks.peek();

      const allCaptions: Array<{
        text: string;
        startMs: number;
        endMs: number;
        timestampMs: number | null;
        confidence: number | null;
      }> = [];

      for (const track of editorTracks) {
        for (const item of track.items) {
          if (item.type !== "video") continue;
          const itemCaptions = captionsSnapshot[item.id];
          if (!itemCaptions?.length) continue;
          const itemStartMs = (item.from / EDITOR_FPS) * 1000;
          for (const cap of itemCaptions) {
            allCaptions.push({
              ...cap,
              startMs: cap.startMs + itemStartMs,
              endMs: cap.endMs + itemStartMs,
              timestampMs:
                cap.timestampMs != null
                  ? cap.timestampMs + itemStartMs
                  : null,
            });
          }
        }
      }

      // Use first video item's style for the exported track, or DEFAULT_STYLE
      const firstVideoId = editorTracks
        .flatMap((t) => t.items)
        .find((i) => i.type === "video")?.id;
      const exportStyle = firstVideoId
        ? (stylesSnapshot[firstVideoId] ?? DEFAULT_STYLE)
        : DEFAULT_STYLE;

      // Sort captions chronologically for correct subtitle paging
      allCaptions.sort((a, b) => a.startMs - b.startMs);

      const subtitles =
        allCaptions.length > 0
          ? { captions: allCaptions, style: exportStyle }
          : null;

      const compositionJson = getCompositionJSON(subtitles);

      // Client-side pre-validation for immediate feedback
      const clientValidation = videoCompositionSchema.safeParse(compositionJson);
      if (!clientValidation.success) {
        console.error(
          "Client-side composition validation failed:",
          clientValidation.error.issues
        );
        toast.error(
          "Export data validation failed. Please check your timeline and try again."
        );
        return;
      }

      const response = await fetch("/api/clips/create-v2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clipId,
          compositionJson,
          teamId: teamId ?? undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Export failed");
      }

      // Save clipId before resetting stores
      const clipIdToClean = clipId;

      // Reset all stores to clear timeline and subtitles
      resetEditor();
      resetSubtitleStore();
      resetPlayerStore();

      // Clear localStorage draft
      try {
        localStorage.removeItem(`remotion-editor-${clipIdToClean}`);
      } catch {
        /* ignore localStorage errors */
      }

      toast.success("Export started! Your clip is being rendered.");

      // Redirect to the new clip page
      router.push(`/dashboard/my-clips/${data.userClipId}`);
    } catch (error) {
      ErrorLogger.logError(error, {
        component: "ExportTab",
        action: "export",
        feature: "remotion-editor",
        additionalContext: { clipId },
      });
      const message =
        error instanceof Error ? error.message : "Export failed";
      toast.error(message);
    } finally {
      setExporting(false);
    }
  }, [clipId, totalDurationInFrames, teamId, router]);

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {/* Summary */}
        <div className="space-y-2">
          <Label className="text-xs font-medium">Export Summary</Label>
          <div className="rounded-md border border-border p-3 space-y-2">
            <SummaryRow
              icon={<Monitor className="h-3.5 w-3.5" />}
              label="Formats"
              value="16:9 + 9:16"
            />
            <SummaryRow
              icon={<Maximize2 className="h-3.5 w-3.5" />}
              label="Resolutions"
              value="1920x1080 + 1080x1920"
            />
            <SummaryRow
              icon={<Clock className="h-3.5 w-3.5" />}
              label="Duration"
              value={`${durationSeconds}s`}
            />
            <SummaryRow
              icon={<Film className="h-3.5 w-3.5" />}
              label="Video clips"
              value={String(videoItemCount)}
            />
            {textItemCount > 0 && (
              <SummaryRow
                icon={<Type className="h-3.5 w-3.5" />}
                label="Text overlays"
                value={String(textItemCount)}
              />
            )}

            <Separator />

            <SummaryRow
              icon={<Captions className="h-3.5 w-3.5" />}
              label="Subtitles"
              value={hasSubtitles ? "Yes" : "None"}
            />
            {imageItemCount > 0 && (
              <SummaryRow
                icon={<ImageIcon className="h-3.5 w-3.5" />}
                label="Image overlays"
                value={String(imageItemCount)}
              />
            )}
          </div>
        </div>

        {/* Export button */}
        <Button
          className="w-full"
          onClick={handleExport}
          disabled={exporting || totalDurationInFrames === 0}
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          {exporting ? "Exporting..." : "Export Video"}
        </Button>

        {/* Info */}
        <div className="bg-muted/50 rounded-md p-3 flex gap-2">
          <Info className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              Export sends your composition to the render queue. Both 16:9
              and 9:16 versions will be rendered.
            </p>
            <p className="text-xs text-muted-foreground">
              Processing typically takes 1-3 minutes depending on clip length.
            </p>
          </div>
        </div>
      </div>
    </ScrollArea>
  );
}

export const ExportTab = observer(ExportTabInner);
