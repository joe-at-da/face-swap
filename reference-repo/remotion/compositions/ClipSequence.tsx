import { useMemo, useRef, useEffect } from "react";
import { OffthreadVideo, useCurrentFrame, interpolate } from "remotion";
import type { TimelineItem, ItemTransform, Keyframe } from "@/types/remotionEditor";

interface ClipSequenceProps {
  item: TimelineItem;
  seekDelay?: number;
}

/**
 * Compute the CSS transform string from an ItemTransform + flip flags.
 */
function computeTransformStyle(
  t: ItemTransform,
  flipH?: boolean,
  flipV?: boolean
): string {
  const parts: string[] = [];
  if (t.translateX != null || t.translateY != null) {
    parts.push(`translate(${t.translateX ?? 0}%, ${t.translateY ?? 0}%)`);
  }
  if (t.scale != null && t.scale !== 1) {
    parts.push(`scale(${t.scale})`);
  }
  if (t.rotation != null && t.rotation !== 0) {
    parts.push(`rotate(${t.rotation}deg)`);
  }
  if (flipH) parts.push("scaleX(-1)");
  if (flipV) parts.push("scaleY(-1)");
  return parts.length > 0 ? parts.join(" ") : "none";
}

/**
 * Build a CSS filter string from video filters.
 */
function computeFilterStyle(filters?: {
  brightness?: number;
  contrast?: number;
  saturation?: number;
}): string | undefined {
  if (!filters) return undefined;
  const parts: string[] = [];
  if (filters.brightness != null && filters.brightness !== 1) {
    parts.push(`brightness(${filters.brightness})`);
  }
  if (filters.contrast != null && filters.contrast !== 1) {
    parts.push(`contrast(${filters.contrast})`);
  }
  if (filters.saturation != null && filters.saturation !== 1) {
    parts.push(`saturate(${filters.saturation})`);
  }
  return parts.length > 0 ? parts.join(" ") : undefined;
}

/**
 * Interpolate between keyframes at the given frame.
 * Returns the interpolated transform for smooth Ken Burns effects.
 */
function interpolateKeyframes(
  keyframes: Keyframe[],
  frame: number
): ItemTransform {
  if (keyframes.length === 0) return {};
  if (keyframes.length === 1) return keyframes[0].transform;

  // Sort by frame
  const sorted = [...keyframes].sort((a, b) => a.frame - b.frame);

  // Before first keyframe
  if (frame <= sorted[0].frame) return sorted[0].transform;

  // After last keyframe
  if (frame >= sorted[sorted.length - 1].frame) {
    return sorted[sorted.length - 1].transform;
  }

  // Find the two surrounding keyframes
  let prev = sorted[0];
  let next = sorted[1];
  for (let i = 0; i < sorted.length - 1; i++) {
    if (frame >= sorted[i].frame && frame <= sorted[i + 1].frame) {
      prev = sorted[i];
      next = sorted[i + 1];
      break;
    }
  }

  const progress = interpolate(
    frame,
    [prev.frame, next.frame],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return {
    scale: interpolateVal(prev.transform.scale, next.transform.scale, progress),
    translateX: interpolateVal(prev.transform.translateX, next.transform.translateX, progress),
    translateY: interpolateVal(prev.transform.translateY, next.transform.translateY, progress),
    rotation: interpolateVal(prev.transform.rotation, next.transform.rotation, progress),
  };
}

function interpolateVal(
  a: number | undefined,
  b: number | undefined,
  t: number
): number | undefined {
  if (a == null && b == null) return undefined;
  const from = a ?? (b ?? 0);
  const to = b ?? (a ?? 0);
  return from + (to - from) * t;
}

export const ClipSequence: React.FC<ClipSequenceProps> = ({ item, seekDelay }) => {
  const frame = useCurrentFrame();
  const containerRef = useRef<HTMLDivElement>(null);

  // Compute transform from keyframes or static transform
  // Must be called before early returns to satisfy React hooks rules
  const transform = useMemo(() => {
    if (item.keyframes && item.keyframes.length > 0) {
      return interpolateKeyframes(item.keyframes, frame);
    }
    return item.transform ?? {};
  }, [item.keyframes, item.transform, frame]);

  // During premount (frame < 0), Remotion mounts the <video> element but
  // doesn't seek it to the startFrom position. We force-seek it so the
  // browser fetches the correct byte range early and caches it.
  const isPremounting = frame < 0;
  useEffect(() => {
    if (!isPremounting || !item.src) return;

    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let delayId: ReturnType<typeof setTimeout> | null = null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const trySeek = () => {
      if (cancelled) return;
      const videoEl = container.querySelector("video");
      if (!videoEl) {
        timeoutId = setTimeout(trySeek, 50);
        return;
      }

      videoEl.preload = "auto";
      const seekSec = (item.startFrom ?? 0) / 30;

      if (videoEl.readyState >= 1) {
        videoEl.currentTime = seekSec;
      } else {
        videoEl.addEventListener(
          "loadedmetadata",
          () => {
            if (!cancelled) videoEl.currentTime = seekSec;
          },
          { once: true }
        );
      }
    };

    // Stagger the seek for overlapping clips to avoid competing Range requests
    delayId = setTimeout(() => trySeek(), seekDelay ?? 0);

    return () => {
      cancelled = true;
      if (delayId) clearTimeout(delayId);
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [isPremounting, item.startFrom, item.src, seekDelay]);

  if (!item.src) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          backgroundColor: "#1a1a2e",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#666",
          fontSize: 16,
        }}
      >
        No video source
      </div>
    );
  }

  const transformStyle = computeTransformStyle(transform, item.flipH, item.flipV);
  const filterStyle = computeFilterStyle(item.filters);
  const baseVolume = item.isMuted ? 0 : (item.volume ?? 1);
  const baseOpacity = item.opacity ?? 1;

  // Audio fade durations (configurable, default 0 = no fade)
  const fadeIn = item.audioFadeIn ?? 0;
  const fadeOut = item.audioFadeOut ?? 0;
  const dur = item.durationInFrames;

  // Volume function with fade in/out (only when fades are set and clip is long enough)
  let volumeFn: number | ((f: number) => number) = baseVolume;
  if (baseVolume > 0 && (fadeIn > 0 || fadeOut > 0) && dur > fadeIn + fadeOut) {
    volumeFn = (f: number) =>
      interpolate(
        f,
        [0, Math.max(fadeIn, 1), dur - Math.max(fadeOut, 1), dur],
        [fadeIn > 0 ? 0 : baseVolume, baseVolume, baseVolume, fadeOut > 0 ? 0 : baseVolume],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      );
  }

  // Visual fade (opacity) — uses the same durations as audio fade
  let visualOpacity = baseOpacity;
  if ((fadeIn > 0 || fadeOut > 0) && dur > fadeIn + fadeOut) {
    visualOpacity =
      baseOpacity *
      interpolate(
        frame,
        [0, Math.max(fadeIn, 1), dur - Math.max(fadeOut, 1), dur],
        [fadeIn > 0 ? 0 : 1, 1, 1, fadeOut > 0 ? 0 : 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      );
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        overflow: "hidden",
        opacity: visualOpacity !== 1 ? visualOpacity : undefined,
      }}
    >
      <OffthreadVideo
        src={item.src}
        startFrom={item.startFrom ?? 0}
        endAt={item.endAt}
        playbackRate={item.playbackRate ?? 1}
        volume={volumeFn}
        muted={item.isMuted ?? false}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: transformStyle !== "none" ? transformStyle : undefined,
          transformOrigin: "center center",
          filter: filterStyle,
        }}
      />
    </div>
  );
};
