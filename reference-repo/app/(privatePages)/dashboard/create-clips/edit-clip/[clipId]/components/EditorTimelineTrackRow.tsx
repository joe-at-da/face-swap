"use client";

import { useMemo } from "react";
import { useRow } from "dnd-timeline";
import type { Span } from "dnd-timeline";
import { ChevronUp, ChevronDown, Film, Type, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { observer } from "@legendapp/state/react";
import { reorderTrack, removeTrack, selectTrack, editor$ } from "@/stores/editorStore";
import { EditorTimelineClipBlock } from "./EditorTimelineClipBlock";
import { EDITOR_FPS } from "@/lib/editorConstants";

interface EditorTimelineTrackRowProps {
  trackId: string;
  trackIndex: number;
  isFirst: boolean;
  isLast: boolean;
}

/** Convert a TimelineItem's frame-based position to a dnd-timeline Span (ms). */
function itemToSpan(item: { from: number; durationInFrames: number }): Span {
  return {
    start: (item.from / EDITOR_FPS) * 1000,
    end: ((item.from + item.durationInFrames) / EDITOR_FPS) * 1000,
  };
}

/** Determine dominant item type in a track. */
function getTrackType(items: Array<{ type: string }>): "video" | "text" | "mixed" {
  if (items.length === 0) return "mixed";
  const videoCount = items.filter((i) => i.type === "video").length;
  const textCount = items.filter((i) => i.type === "text").length;
  if (videoCount > 0 && textCount === 0) return "video";
  if (textCount > 0 && videoCount === 0) return "text";
  return "mixed";
}

export const EditorTimelineTrackRow = observer(function EditorTimelineTrackRow({ trackId, trackIndex, isFirst, isLast }: EditorTimelineTrackRowProps) {
  // Read directly from the observable so observer() detects nested changes
  const track = editor$.tracks[trackIndex].get();

  const {
    setNodeRef,
    setSidebarRef,
    rowWrapperStyle,
    rowStyle,
    rowSidebarStyle,
  } = useRow({ id: trackId });

  const selectedTrackId = editor$.selectedTrackId.get();
  const isSelected = selectedTrackId === trackId;

  const trackLabel = `${trackIndex + 1}`;
  const trackType = getTrackType(track.items);

  const TrackIcon = trackType === "video" ? Film : trackType === "text" ? Type : null;

  const borderColor =
    trackType === "video"
      ? "border-l-primary"
      : trackType === "text"
        ? "border-l-chart-3"
        : "border-l-border";

  const trackCount = editor$.tracks.get().length;
  const canDelete = track.items.length === 0 && trackCount > 1;

  // Memoize spans to avoid recalculating on every render
  const itemsWithSpans = useMemo(
    () => track.items.map((item) => ({ item, span: itemToSpan(item) })),
    [track.items]
  );

  return (
    <div style={{ ...rowWrapperStyle, minHeight: 40 }}>
      {/* Sidebar: track icon + label + reorder */}
      <div
        ref={setSidebarRef}
        style={rowSidebarStyle}
        className={cn(
          "group/sidebar flex flex-col items-center justify-center w-12 border-r border-border border-l-2 relative cursor-pointer",
          borderColor,
          isSelected ? "bg-primary/10 border-r-primary" : "bg-muted/50"
        )}
        onClick={() => selectTrack(isSelected ? null : trackId)}
      >
        {TrackIcon && (
          <TrackIcon className={cn(
            "h-3 w-3 mb-0.5",
            isSelected ? "text-primary" : "text-muted-foreground"
          )} />
        )}
        <span className={cn(
          "text-[10px] font-semibold",
          isSelected ? "text-primary" : "text-muted-foreground"
        )}>
          {trackLabel}
        </span>
        {/* Reorder arrows — visible on hover */}
        <div className="absolute right-0 top-0 bottom-0 flex flex-col justify-center opacity-0 group-hover/sidebar:opacity-100 transition-opacity">
          {!isFirst && (
            <button
              onClick={(e) => { e.stopPropagation(); reorderTrack(trackId, "up"); }}
              className="p-0 h-3 flex items-center text-muted-foreground hover:text-foreground"
            >
              <ChevronUp className="h-3 w-3" />
            </button>
          )}
          {!isLast && (
            <button
              onClick={(e) => { e.stopPropagation(); reorderTrack(trackId, "down"); }}
              className="p-0 h-3 flex items-center text-muted-foreground hover:text-foreground"
            >
              <ChevronDown className="h-3 w-3" />
            </button>
          )}
          {canDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); removeTrack(trackId); }}
              className="p-0 h-3 flex items-center text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {/* Track content area */}
      <div
        ref={setNodeRef}
        style={{ ...rowStyle, position: "relative", minHeight: 40 }}
        className={cn(
          "border-b border-border/50",
          isSelected && "bg-primary/5"
        )}
      >
        {itemsWithSpans.map(({ item, span }) => (
          <EditorTimelineClipBlock
            key={item.id}
            item={item}
            span={span}
          />
        ))}
      </div>
    </div>
  );
});
