"use client";

import { useMemo } from "react";
import { useTimelineContext } from "dnd-timeline";

function formatTime(ms: number): string {
  const totalSeconds = ms / 1000;
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function EditorTimelineRuler() {
  const { range, valueToPixels } = useTimelineContext();

  const marks = useMemo(() => {
    const rangeMs = range.end - range.start;
    // Choose interval based on zoom level
    let intervalMs: number;
    if (rangeMs < 5000) {
      intervalMs = 500; // 0.5s intervals for very zoomed in
    } else if (rangeMs < 30000) {
      intervalMs = 1000; // 1s intervals
    } else if (rangeMs < 120000) {
      intervalMs = 5000; // 5s intervals
    } else if (rangeMs < 600000) {
      intervalMs = 30000; // 30s intervals
    } else {
      intervalMs = 60000; // 1min intervals
    }

    const result: Array<{ ms: number; px: number; label: string; major: boolean }> = [];
    const startMs = Math.ceil(range.start / intervalMs) * intervalMs;

    for (let ms = startMs; ms <= range.end; ms += intervalMs) {
      const px = valueToPixels(ms - range.start);
      const isMajor = ms % (intervalMs * 5) === 0 || intervalMs >= 30000;
      result.push({
        ms,
        px,
        label: formatTime(ms),
        major: isMajor,
      });
    }

    return result;
  }, [range, valueToPixels]);

  return (
    <div className="relative h-7 border-b border-border bg-muted/30 select-none overflow-hidden">
      {marks.map((mark) => (
        <div
          key={mark.ms}
          className="absolute top-0 h-full"
          style={{ left: `calc(2.5rem + ${mark.px}px)` }}
        >
          <div
            className={
              mark.major
                ? "w-px h-4 bg-muted-foreground/80"
                : "w-px h-2.5 bg-muted-foreground/40"
            }
          />
          {mark.major && (
            <span className="absolute top-3 left-0.5 text-[10px] text-muted-foreground whitespace-nowrap">
              {mark.label}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
