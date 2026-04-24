"use client";

import { useCallback } from "react";
import { useItem, type Span } from "dnd-timeline";
import { observer } from "@legendapp/state/react";
import { Film, Type } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TimelineItem } from "@/types/remotionEditor";
import { selectItem, editor$ } from "@/stores/editorStore";
import { EDITOR_FPS } from "@/lib/editorConstants";

interface EditorTimelineClipBlockProps {
  item: TimelineItem;
  span: Span;
}

function formatDuration(frames: number): string {
  const totalSeconds = frames / EDITOR_FPS;
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  if (m > 0) return `${m}:${s.toString().padStart(2, "0")}`;
  return `${s}s`;
}

function EditorTimelineClipBlockInner({
  item,
  span,
}: EditorTimelineClipBlockProps) {
  const selectedItemId = editor$.selectedItemId.get();
  const isSelected = selectedItemId === item.id;

  const { setNodeRef, attributes, listeners, itemStyle, itemContentStyle } =
    useItem({
      id: item.id,
      span,
      resizeHandleWidth: 8,
    });

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      selectItem(item.id);
    },
    [item.id]
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();
      selectItem(item.id);
    },
    [item.id]
  );

  const bgColor =
    item.type === "video"
      ? "bg-primary/80"
      : item.type === "text"
        ? "bg-chart-3/80"
        : "bg-chart-4/80";

  const ItemIcon = item.type === "video" ? Film : item.type === "text" ? Type : null;
  const speedLabel = item.playbackRate && item.playbackRate !== 1
    ? `${item.playbackRate}x`
    : null;

  return (
    <div
      ref={setNodeRef}
      style={itemStyle}
      {...listeners}
      {...attributes}
      className="group"
    >
      <div style={itemContentStyle} className="h-full">
        <div
          onClick={handleClick}
          onDoubleClick={handleDoubleClick}
          className={cn(
            "h-full w-full rounded-md border overflow-hidden cursor-grab active:cursor-grabbing select-none relative",
            "flex items-center px-1.5 gap-1",
            bgColor,
            isSelected
              ? "border-primary ring-1 ring-primary"
              : "border-border/50 hover:border-border"
          )}
        >
          {/* Gradient overlay for depth */}
          <div className="absolute inset-0 bg-gradient-to-b from-white/10 to-transparent pointer-events-none" />

          {/* Left resize handle */}
          <div className="absolute left-0 top-1 bottom-1 w-1.5 bg-white/20 rounded-full group-hover:bg-white/40 cursor-col-resize transition-colors" />

          {/* Content */}
          {ItemIcon && (
            <ItemIcon className="h-3 w-3 text-primary-foreground/70 flex-shrink-0 relative z-10" />
          )}
          <span className="text-[11px] font-medium text-primary-foreground truncate leading-tight relative z-10">
            {item.sourceClip?.mpName ?? item.text ?? item.type}
          </span>
          <span className="text-[9px] text-primary-foreground/70 shrink-0 relative z-10">
            {formatDuration(item.durationInFrames)}
          </span>

          {/* Speed badge */}
          {speedLabel && (
            <span className="absolute bottom-0.5 right-1.5 text-[8px] bg-black/30 text-primary-foreground rounded px-0.5 z-10">
              {speedLabel}
            </span>
          )}

          {/* Right resize handle */}
          <div className="absolute right-0 top-1 bottom-1 w-1.5 bg-white/20 rounded-full group-hover:bg-white/40 cursor-col-resize transition-colors" />
        </div>
      </div>
    </div>
  );
}

export const EditorTimelineClipBlock = observer(EditorTimelineClipBlockInner);
