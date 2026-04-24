"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  TimelineContext,
  useTimelineContext,
  useRow,
  type Range,
  type DragEndEvent,
  type ResizeEndEvent,
} from "dnd-timeline";
import { useDndContext, PointerSensor, useSensors, useSensor } from "@dnd-kit/core";
import { TooltipProvider } from "@/components/ui/tooltip";
import { observer } from "@legendapp/state/react";
import type { PlayerRef } from "@remotion/player";
import {
  editor$,
  moveItem,
  trimItem,
  resolveTargetItem,
  findAllItemsAtFrame,
  splitItem,
  selectItem,
  addTrack,
  getSnapTargets,
  snapToEdge,
  showSnapIndicator,
} from "@/stores/editorStore";
import { player$, beginSeek } from "@/stores/remotionPlayerStore";
import { EditorTimelineTrackRow } from "./EditorTimelineTrackRow";
import { EditorTimelineRuler } from "./EditorTimelineRuler";
import { EditorTimelinePlayhead } from "./EditorTimelinePlayhead";
import { EditorTimelineToolbar } from "./EditorTimelineToolbar";
import { useEditorKeyboard } from "../hooks/useEditorKeyboard";
import { EDITOR_FPS } from "@/lib/editorConstants";

const PADDING_MS = 2000; // 2s padding at the end of the timeline
const DROP_ZONE_ID = "__new-track-drop-zone__";

/** Convert frames to milliseconds. */
function framesToMs(frames: number): number {
  return (frames / EDITOR_FPS) * 1000;
}

/** Convert milliseconds to frames. */
function msToFrames(ms: number): number {
  return Math.round((ms / 1000) * EDITOR_FPS);
}

/** Ghost row that appears when dragging — drop here to create a new track. */
function DropZoneRow() {
  const { active } = useDndContext();
  const isDragging = active !== null;

  const { setNodeRef, rowWrapperStyle, rowStyle } = useRow({ id: DROP_ZONE_ID });

  if (!isDragging) {
    // Collapsed placeholder so dnd-timeline keeps the row registered
    return (
      <div style={{ ...rowWrapperStyle, minHeight: 4 }}>
        <div ref={setNodeRef} style={{ ...rowStyle, height: 4 }} />
      </div>
    );
  }

  return (
    <div style={{ ...rowWrapperStyle, minHeight: 40 }}>
      <div
        ref={setNodeRef}
        style={{ ...rowStyle, position: "relative", minHeight: 40 }}
        className="border-2 border-dashed border-primary/40 rounded-md bg-primary/5 flex items-center justify-center transition-all"
      >
        <span className="text-xs text-primary/60 pointer-events-none">
          Drop here to add new track
        </span>
      </div>
    </div>
  );
}

interface EditorTimelineProps {
  playerRef: React.RefObject<PlayerRef | null>;
}

/** Inner timeline that has access to useTimelineContext. */
function TimelineContent({
  playerRef,
}: EditorTimelineProps) {
  const { setTimelineRef, style } = useTimelineContext();
  const tracks = editor$.tracks.get();

  const handleSeek = useCallback(
    (frame: number) => {
      const player = playerRef.current;
      if (!player) return;
      beginSeek();
      player.seekTo(frame);
      player$.currentFrame.set(frame);
    },
    [playerRef]
  );

  return (
    <div className="relative flex flex-col h-full">
      {/* Ruler */}
      <EditorTimelineRuler />

      {/* Track area */}
      <div
        className="flex-1 min-h-0 relative"
        ref={setTimelineRef}
        style={{ ...style, overflowY: 'auto', overflowX: 'hidden' }}
      >
        {tracks.map((track, index) => (
          <EditorTimelineTrackRow
            key={track.id}
            trackId={track.id}
            trackIndex={index}
            isFirst={index === 0}
            isLast={index === tracks.length - 1}
          />
        ))}

        {/* Ghost drop-zone row — expands during drag */}
        <DropZoneRow />

        {/* Empty state */}
        {tracks.every((t) => t.items.length === 0) && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-xs text-muted-foreground">
              No clips yet. Add clips from the side panel.
            </p>
          </div>
        )}
      </div>

      {/* Playhead overlay */}
      <EditorTimelinePlayhead onSeek={handleSeek} />
    </div>
  );
}

const ObservedTimelineContent = observer(TimelineContent);

/** Main EditorTimeline wrapper with TimelineContext provider. */
function EditorTimelineInner({ playerRef }: EditorTimelineProps) {
  const totalDurationInFrames = editor$.totalDurationInFrames.get();
  const zoomLevel = editor$.zoomLevel.get();

  // Require 5px movement before drag starts — prevents micro-drags on double-click
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // Track whether user has manually zoomed/panned
  const isRangeInitialized = useRef(false);

  const [range, setRange] = useState<Range>(() => {
    const totalMs = framesToMs(totalDurationInFrames) + PADDING_MS;
    return { start: 0, end: Math.max(totalMs, 5000) };
  });

  // Update range when total duration changes (auto-fit if user hasn't manually zoomed)
  useEffect(() => {
    if (!isRangeInitialized.current) {
      const totalMs = framesToMs(totalDurationInFrames) + PADDING_MS;
      setRange({ start: 0, end: Math.max(totalMs, 5000) });
    }
  }, [totalDurationInFrames]);

  // Apply zoom level to range: scale proportionally around center
  const prevZoomRef = useRef(zoomLevel);
  useEffect(() => {
    const prevZoom = prevZoomRef.current;
    if (zoomLevel !== prevZoom && prevZoom > 0) {
      isRangeInitialized.current = true;
      const ratio = prevZoom / zoomLevel;
      setRange((prev) => {
        const center = (prev.start + prev.end) / 2;
        const halfRange = ((prev.end - prev.start) / 2) * ratio;
        const newStart = Math.max(0, center - halfRange);
        const newEnd = newStart + halfRange * 2;
        return { start: newStart, end: newEnd };
      });
    }
    prevZoomRef.current = zoomLevel;
  }, [zoomLevel]);

  const handleRangeChanged = useCallback((updateFn: (prev: Range) => Range) => {
    isRangeInitialized.current = true;
    setRange(updateFn);
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const activeRowId = event.over?.id as string | undefined;
    const updatedSpan = event.active.data.current?.getSpanFromDragEvent?.(event);
    if (!updatedSpan) return;

    const itemId = event.active.id as string;
    let newFromFrame = msToFrames(updatedSpan.start);

    // Apply snapping to both the start and end edges
    const snapTargets = getSnapTargets(itemId);
    snapTargets.push(player$.currentFrame.peek());

    // Find the item to know its duration for end-edge snapping
    const tracks = editor$.tracks.peek();
    let itemDuration = 0;
    for (const track of tracks) {
      const found = track.items.find((i) => i.id === itemId);
      if (found) {
        itemDuration = found.durationInFrames;
        break;
      }
    }

    const startSnap = snapToEdge(newFromFrame, snapTargets);
    const endFrame = newFromFrame + itemDuration;
    const endSnap = snapToEdge(endFrame, snapTargets);

    // Use whichever snap is closer (prefer start edge on tie)
    if (
      startSnap.snappedTo !== null &&
      (endSnap.snappedTo === null ||
        Math.abs(newFromFrame - startSnap.frame) <=
          Math.abs(endFrame - endSnap.frame))
    ) {
      newFromFrame = startSnap.frame;
      showSnapIndicator(startSnap.snappedTo);
    } else if (endSnap.snappedTo !== null) {
      newFromFrame = endSnap.frame - itemDuration;
      showSnapIndicator(endSnap.snappedTo);
    } else {
      showSnapIndicator(null);
    }

    if (activeRowId === DROP_ZONE_ID) {
      const newTrack = addTrack();
      moveItem(itemId, newFromFrame, newTrack.id);
    } else {
      moveItem(itemId, newFromFrame, activeRowId);
    }
  }, []);

  const handleResizeEnd = useCallback((event: ResizeEndEvent) => {
    const updatedSpan = event.active.data.current?.getSpanFromResizeEvent?.(event);
    if (!updatedSpan) return;

    const itemId = event.active.id as string;
    const direction = event.direction;

    // Find the current item to calculate delta
    const tracks = editor$.tracks.peek();
    let currentItem = null;
    for (const track of tracks) {
      const found = track.items.find((i) => i.id === itemId);
      if (found) {
        currentItem = found;
        break;
      }
    }
    if (!currentItem) return;

    // Collect snap targets (exclude current item, include playhead)
    const snapTargets = getSnapTargets(itemId);
    snapTargets.push(player$.currentFrame.peek());

    if (direction === "start") {
      let newStartFrame = msToFrames(updatedSpan.start);
      const startSnap = snapToEdge(newStartFrame, snapTargets);
      if (startSnap.snappedTo !== null) {
        newStartFrame = startSnap.frame;
        showSnapIndicator(startSnap.snappedTo);
      } else {
        showSnapIndicator(null);
      }
      const deltaFrames = newStartFrame - currentItem.from;
      if (deltaFrames !== 0) {
        trimItem(itemId, "start", deltaFrames);
      }
    } else {
      let newEndFrame = msToFrames(updatedSpan.end);
      const endSnap = snapToEdge(newEndFrame, snapTargets);
      if (endSnap.snappedTo !== null) {
        newEndFrame = endSnap.frame;
        showSnapIndicator(endSnap.snappedTo);
      } else {
        showSnapIndicator(null);
      }
      const currentEndFrame = currentItem.from + currentItem.durationInFrames;
      const deltaFrames = newEndFrame - currentEndFrame;
      if (deltaFrames !== 0) {
        trimItem(itemId, "end", deltaFrames);
      }
    }
  }, []);

  const handleSplitAtPlayhead = useCallback(() => {
    const currentFrame = player$.currentFrame.peek();
    const item = resolveTargetItem(currentFrame);
    if (item) {
      splitItem(item.id, currentFrame);
      // Auto-select next item that can actually be split at this frame
      const remaining = findAllItemsAtFrame(currentFrame).filter(
        (i) => i.id !== item.id && currentFrame > i.from
      );
      if (remaining.length > 0) {
        selectItem(remaining[0].id);
      }
    }
  }, []);

  const handleFitToView = useCallback(() => {
    isRangeInitialized.current = false;
    const totalMs = framesToMs(editor$.totalDurationInFrames.peek()) + PADDING_MS;
    setRange({ start: 0, end: Math.max(totalMs, 5000) });
  }, []);

  // Keyboard shortcuts
  useEditorKeyboard({ playerRef });

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex flex-col h-full bg-background">
        <div className="flex-1 min-h-0 overflow-hidden">
          <TimelineContext
            range={range}
            onRangeChanged={handleRangeChanged}
            onDragEnd={handleDragEnd}
            onResizeEnd={handleResizeEnd}
            resizeHandleWidth={12}
            sensors={sensors}
          >
            <ObservedTimelineContent playerRef={playerRef} />
          </TimelineContext>
        </div>

        {/* Toolbar */}
        <EditorTimelineToolbar
          onSplitAtPlayhead={handleSplitAtPlayhead}
          onFitToView={handleFitToView}
        />
      </div>
    </TooltipProvider>
  );
}

export const EditorTimeline = observer(EditorTimelineInner);
