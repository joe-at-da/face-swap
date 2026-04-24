"use client";

import { useCallback, useEffect, useRef } from "react";
import { useTimelineContext } from "dnd-timeline";
import { observer } from "@legendapp/state/react";
import { player$ } from "@/stores/remotionPlayerStore";
import { editor$ } from "@/stores/editorStore";
import { EDITOR_FPS } from "@/lib/editorConstants";

interface EditorTimelinePlayheadProps {
  onSeek: (frame: number) => void;
}

function formatPlayheadTime(frame: number): string {
  const totalSeconds = frame / EDITOR_FPS;
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Playhead with ref-based DOM updates to avoid 30fps React re-renders.
 *
 * The playhead line + time text update via direct DOM manipulation
 * inside a Legend State onChange listener. Only the snap indicator
 * (which changes infrequently) uses React state via observer().
 */
function EditorTimelinePlayheadInner({
  onSeek,
}: EditorTimelinePlayheadProps) {
  const { valueToPixels, range, getValueFromScreenX } =
    useTimelineContext();

  // Refs for direct DOM updates (bypass React re-renders)
  const playheadRef = useRef<HTMLDivElement>(null);
  const timeTextRef = useRef<HTMLDivElement>(null);

  // Keep range in a ref so the onChange callback always sees current values
  const rangeRef = useRef(range);
  const valueToPixelsRef = useRef(valueToPixels);

  useEffect(() => {
    rangeRef.current = range;
    valueToPixelsRef.current = valueToPixels;
  });

  // Subscribe to frame changes and update DOM directly
  useEffect(() => {
    const dispose = player$.currentFrame.onChange((e) => {
      const frame = e.value ?? 0;
      const currentMs = (frame / EDITOR_FPS) * 1000;
      const r = rangeRef.current;
      const isVisible = currentMs >= r.start && currentMs <= r.end;

      if (playheadRef.current) {
        if (isVisible) {
          const px = valueToPixelsRef.current(currentMs - r.start);
          playheadRef.current.style.left = `calc(3rem + ${px}px)`;
          playheadRef.current.style.display = "";
        } else {
          playheadRef.current.style.display = "none";
        }
      }

      if (timeTextRef.current) {
        timeTextRef.current.textContent = formatPlayheadTime(frame);
      }
    });

    return dispose;
  }, []);

  // Set initial position from current frame
  const initialFrame = player$.currentFrame.peek();
  const initialMs = (initialFrame / EDITOR_FPS) * 1000;
  const initialPx = valueToPixels(initialMs - range.start);
  const initialVisible = initialMs >= range.start && initialMs <= range.end;

  // Snap indicator (changes infrequently — fine to use observer reactivity)
  const snapIndicatorFrame = editor$.snapIndicatorFrame.get();
  const snapMs = snapIndicatorFrame !== null ? (snapIndicatorFrame / EDITOR_FPS) * 1000 : null;
  const snapPx = snapMs !== null ? valueToPixels(snapMs - range.start) : 0;
  const snapVisible = snapMs !== null && snapMs >= range.start && snapMs <= range.end;

  const handleRulerClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const ms = getValueFromScreenX(e.clientX);
      const frame = Math.round((ms / 1000) * EDITOR_FPS);
      onSeek(Math.max(0, frame));
    },
    [getValueFromScreenX, onSeek]
  );

  return (
    <>
      {/* Clickable ruler overlay for seeking */}
      <div
        className="absolute top-0 left-12 right-0 h-7 z-10 cursor-pointer"
        onClick={handleRulerClick}
      />

      {/* Snap indicator line */}
      {snapVisible && (
        <div
          className="absolute top-0 bottom-0 z-15 pointer-events-none"
          style={{ left: `calc(3rem + ${snapPx}px)` }}
        >
          <div
            className="w-0.5 h-full bg-chart-3 animate-pulse"
            style={{ boxShadow: "0 0 6px rgba(34, 197, 94, 0.6)" }}
          />
        </div>
      )}

      {/* Playhead line — positioned via ref, no React re-renders */}
      <div
        ref={playheadRef}
        className="absolute top-0 bottom-0 z-20 pointer-events-none"
        style={{
          left: `calc(3rem + ${initialPx}px)`,
          display: initialVisible ? "" : "none",
        }}
      >
        {/* Time display above head */}
        <div
          ref={timeTextRef}
          className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[9px] font-mono text-destructive whitespace-nowrap select-none"
        >
          {formatPlayheadTime(initialFrame)}
        </div>
        {/* Triangle head */}
        <div className="w-0 h-0 border-l-[6px] border-r-[6px] border-t-[8px] border-l-transparent border-r-transparent border-t-destructive -translate-x-[6px] mt-2.5" />
        {/* Vertical line */}
        <div
          className="w-0.5 h-full bg-destructive -translate-x-[1px]"
          style={{ boxShadow: "0 0 4px rgba(239, 68, 68, 0.5)" }}
        />
      </div>
    </>
  );
}

export const EditorTimelinePlayhead = observer(EditorTimelinePlayheadInner);
