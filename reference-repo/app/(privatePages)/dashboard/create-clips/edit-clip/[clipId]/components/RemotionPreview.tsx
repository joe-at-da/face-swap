"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Player, type PlayerRef } from "@remotion/player";
import {
  MainComposition,
  type MainCompositionProps,
} from "@/remotion/compositions/MainComposition";
import { editor$, selectItem, updateItemProperties } from "@/stores/editorStore";
import { subtitle$, DEFAULT_STYLE } from "@/stores/subtitleStore";
import {
  player$,
  setIsPlaying,
  setCurrentFrame,
  beginSeek,
  endSeek,
} from "@/stores/remotionPlayerStore";
import type { SubtitleTrack, SubtitleStyle, Track, TimelineItem } from "@/types/remotionEditor";
import { observer } from "@legendapp/state/react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Play, Pause, SkipBack, SkipForward } from "lucide-react";
import { InlineTextEditor } from "./InlineTextEditor";
import { ImageTransformOverlay } from "./ImageTransformOverlay";
import { VideoTransformOverlay } from "./VideoTransformOverlay";
import { formatTimecode } from "./formatTimecode";
import { EDITOR_FPS } from "@/lib/editorConstants";


/**
 * Build per-item subtitle tracks (no timestamp offsetting needed).
 * Each video item gets its own SubtitleTrack with captions relative to item start (0ms).
 * These are rendered inside each video's Sequence in MainComposition.
 */
function buildPerItemSubtitles(
  tracks: Track[],
  captionsByItemId: Record<string, import("@/types/remotionEditor").Caption[]>,
  styleByItemId: Record<string, SubtitleStyle>,
  defaultStyle: SubtitleStyle
): Record<string, SubtitleTrack> {
  const result: Record<string, SubtitleTrack> = {};
  for (const track of tracks) {
    for (const item of track.items) {
      if (item.type !== "video") continue;
      const captions = captionsByItemId[item.id];
      if (!captions?.length) continue;
      result[item.id] = {
        captions,
        style: styleByItemId[item.id] ?? defaultStyle,
      };
    }
  }
  return result;
}

// ─── PreviewControls (lightweight observer — re-renders 30fps) ──────────────

interface PreviewControlsProps {
  playerRef: React.RefObject<PlayerRef | null>;
  duration: number;
}

function PreviewControlsInner({ playerRef, duration }: PreviewControlsProps) {
  const isPlaying = player$.isPlaying.get();
  const currentFrame = player$.currentFrame.get();
  // Sync frame updates from Remotion Player to our store
  useEffect(() => {
    const player = playerRef.current;
    if (!player) return;

    const onFrameUpdate = (e: { detail: { frame: number } }) => {
      setCurrentFrame(e.detail.frame);
    };

    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onSeeked = () => endSeek();

    player.addEventListener("frameupdate", onFrameUpdate);
    player.addEventListener("play", onPlay);
    player.addEventListener("pause", onPause);
    player.addEventListener("seeked", onSeeked);

    return () => {
      player.removeEventListener("frameupdate", onFrameUpdate);
      player.removeEventListener("play", onPlay);
      player.removeEventListener("pause", onPause);
      player.removeEventListener("seeked", onSeeked);
    };
  }, [playerRef]);

  const handlePlayPause = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;

    if (isPlaying) {
      player.pause();
    } else {
      player.play();
    }
  }, [playerRef, isPlaying]);

  const handleSeek = useCallback((value: number[]) => {
    const player = playerRef.current;
    if (!player) return;

    beginSeek();
    player.seekTo(value[0]);
  }, [playerRef]);

  const handleSkipBack = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;

    beginSeek();
    const frame = player$.currentFrame.peek();
    const target = Math.max(0, frame - EDITOR_FPS);
    player.seekTo(target);
  }, [playerRef]);

  const handleSkipForward = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;

    beginSeek();
    const frame = player$.currentFrame.peek();
    const target = Math.min(duration - 1, frame + EDITOR_FPS);
    player.seekTo(target);
  }, [playerRef, duration]);

  return (
    <div className="flex-shrink-0 border-t border-border bg-card px-3 py-2">
      {/* Seek Bar */}
      <Slider
        value={[currentFrame]}
        min={0}
        max={Math.max(duration - 1, 1)}
        step={1}
        onValueChange={handleSeek}
        onValueCommit={handleSeek}
        className="mb-2"
      />

      {/* Transport Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleSkipBack}
          >
            <SkipBack className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handlePlayPause}
          >
            {isPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleSkipForward}
          >
            <SkipForward className="h-4 w-4" />
          </Button>
        </div>

        {/* Time Display */}
        <div className="text-xs text-muted-foreground font-mono">
          {formatTimecode(currentFrame)} /{" "}
          {formatTimecode(duration)}
        </div>
      </div>
    </div>
  );
}

const PreviewControls = observer(PreviewControlsInner);

// ─── Hit-testing helper ──────────────────────────────────────────────────────

/**
 * Find the topmost item at the click position using point-in-bounds + z-order.
 *
 * Iterates in MainComposition render order (videos first, then text — matching
 * tracks.flatMap within each layer). The LAST match is the topmost visually.
 *
 * Video bounds: precise from CSS transform math (translate + scale).
 * Text bounds: estimated from position, fontSize, and text length.
 */
function findTopmostItemAtPoint(
  e: React.MouseEvent,
  frame: number,
  tracks: Track[],
  overlayEl: HTMLDivElement,
  compositionWidth: number,
  compositionHeight: number,
  typeFilter?: "text" | "video" | "image"
): TimelineItem | null {
  const rect = overlayEl.getBoundingClientRect();
  const normX = (e.clientX - rect.left) / rect.width;
  const normY = (e.clientY - rect.top) / rect.height;

  // Build items in z-order matching MainComposition rendering
  const videoItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "video")
  );
  const imageItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "image")
  );
  const textItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "text")
  );
  const ordered = [...videoItems, ...imageItems, ...textItems]; // text > image > video

  let topmost: TimelineItem | null = null;

  for (const item of ordered) {
    if (typeFilter && item.type !== typeFilter) continue;
    if (frame < item.from || frame >= item.from + item.durationInFrames)
      continue;

    if (item.type === "video") {
      // Bounds from ClipSequence: translate(TX%, TY%) scale(S) with transformOrigin center
      const s = item.transform?.scale ?? 1;
      const tx = item.transform?.translateX ?? 0;
      const ty = item.transform?.translateY ?? 0;
      const left = (50 + tx - s * 50) / 100;
      const top = (50 + ty - s * 50) / 100;
      if (
        normX >= left &&
        normX <= left + s &&
        normY >= top &&
        normY <= top + s
      ) {
        topmost = item;
      }
    } else if (item.type === "image") {
      const cx = item.position?.x ?? 0.5;
      const cy = item.position?.y ?? 0.5;
      const imgW = (item.imageWidthPercent ?? 30) / 100;
      const imgH = imgW * 0.75; // approximate aspect ratio
      if (
        normX >= cx - imgW / 2 &&
        normX <= cx + imgW / 2 &&
        normY >= cy - imgH / 2 &&
        normY <= cy + imgH / 2
      ) {
        topmost = item;
      }
    } else if (item.type === "text") {
      // Estimate text bounds from position + fontSize + text length
      const cx = item.position?.x ?? 0.5;
      const cy = item.position?.y ?? 0.5;
      const fontSize = item.fontSize ?? 48;
      const textLen = item.text?.length ?? 5;
      const halfW = Math.min(
        0.4,
        ((textLen * fontSize * 0.35 + 32) / compositionWidth) * 0.5
      );
      const halfH = ((fontSize * 1.5 + 16) / compositionHeight) * 0.5;
      if (
        normX >= cx - halfW &&
        normX <= cx + halfW &&
        normY >= cy - halfH &&
        normY <= cy + halfH
      ) {
        topmost = item;
      }
    }
  }

  return topmost;
}

// ─── VideoOverlayGate (observer — only re-renders on frame changes) ──────────

interface VideoOverlayGateProps {
  item: TimelineItem;
  onDeselect: () => void;
}

function VideoOverlayGateInner({ item, onDeselect }: VideoOverlayGateProps) {
  const currentFrame = player$.currentFrame.get();
  const isVisible =
    currentFrame >= item.from &&
    currentFrame < item.from + item.durationInFrames;

  if (!isVisible) return null;

  return <VideoTransformOverlay item={item} onDeselect={onDeselect} />;
}

const VideoOverlayGate = observer(VideoOverlayGateInner);

// ─── ImageOverlayGate (observer — only re-renders on frame changes) ─────────

interface ImageOverlayGateProps {
  item: TimelineItem;
  onDeselect: () => void;
}

function ImageOverlayGateInner({ item, onDeselect }: ImageOverlayGateProps) {
  const currentFrame = player$.currentFrame.get();
  const isVisible =
    currentFrame >= item.from &&
    currentFrame < item.from + item.durationInFrames;

  if (!isVisible) return null;

  return <ImageTransformOverlay item={item} onDeselect={onDeselect} />;
}

const ImageOverlayGate = observer(ImageOverlayGateInner);

// ─── RemotionPreview (parent — only re-renders on track/config changes) ─────

interface RemotionPreviewProps {
  playerRef: React.RefObject<PlayerRef | null>;
}

function RemotionPreviewInner({ playerRef }: RemotionPreviewProps) {
  const tracks = editor$.tracks.get();
  const totalDurationInFrames = editor$.totalDurationInFrames.get();
  const canvasMode = editor$.canvasMode.get();

  const captionsByItemId = subtitle$.captionsByItemId.get();
  const styleByItemId = subtitle$.styleByItemId.get();

  // Inline text editing state
  const [inlineEditItemId, setInlineEditItemId] = useState<string | null>(null);
  const [inlineEditScale, setInlineEditScale] = useState(1);
  const overlayRef = useRef<HTMLDivElement>(null);
  const pointerDownRef = useRef<{ x: number; y: number } | null>(null);

  const inlineEditItem = useMemo(() => {
    if (!inlineEditItemId) return null;
    for (const track of tracks) {
      const found = track.items.find((i) => i.id === inlineEditItemId);
      if (found) return found;
    }
    return null;
  }, [inlineEditItemId, tracks]);

  // Derive selected video item from store selection
  const selectedItemId = editor$.selectedItemId.get();
  const selectedVideoItem = useMemo(() => {
    if (!selectedItemId || inlineEditItemId) return null;
    for (const track of tracks) {
      const found = track.items.find(
        (i) => i.id === selectedItemId && i.type === "video"
      );
      if (found) return found;
    }
    return null;
  }, [selectedItemId, tracks, inlineEditItemId]);

  // Derive selected image item from store selection
  const selectedImageItem = useMemo(() => {
    if (!selectedItemId || inlineEditItemId) return null;
    for (const track of tracks) {
      const found = track.items.find(
        (i) => i.id === selectedItemId && i.type === "image"
      );
      if (found) return found;
    }
    return null;
  }, [selectedItemId, tracks, inlineEditItemId]);

  const handleVideoDeselect = useCallback(() => {
    selectItem(null);
  }, []);

  const handleImageDeselect = useCallback(() => {
    selectItem(null);
  }, []);

  const compositionWidth = canvasMode === "landscape" ? 1920 : 1080;
  const compositionHeight = canvasMode === "landscape" ? 1080 : 1920;

  // Minimum 1 frame to prevent Remotion errors
  const duration = Math.max(totalDurationInFrames, 1);

  // Build per-item subtitles — computed directly (no useMemo) to avoid stale
  // references from Legend State nested property mutations (.get() returns the
  // same object reference when a child key is .set()). Safe because observer()
  // already limits re-renders to tracked observable changes.
  const subtitlesByItemId = buildPerItemSubtitles(
    tracks,
    captionsByItemId,
    styleByItemId,
    DEFAULT_STYLE
  );

  // Build inputProps inline to stay in sync with subtitlesByItemId.
  // The Player re-renders its composition on every frame anyway.
  const inputProps: MainCompositionProps = {
    tracks,
    subtitlesByItemId,
    inlineEditItemId,
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Player Area — only re-renders on track/config changes */}
      <div className="flex-1 flex items-center justify-center bg-black/90 min-h-0 overflow-hidden p-2">
        <div
          className="relative w-full"
          style={{
            aspectRatio: `${compositionWidth}/${compositionHeight}`,
            maxHeight: "100%",
            maxWidth: "100%",
          }}
        >
          <Player
            ref={playerRef}
            component={MainComposition as unknown as React.ComponentType<Record<string, unknown>>}
            inputProps={inputProps as unknown as Record<string, unknown>}
            durationInFrames={duration}
            fps={EDITOR_FPS}
            compositionWidth={compositionWidth}
            compositionHeight={compositionHeight}
            style={{
              width: "100%",
              height: "100%",
              maxHeight: "100%",
            }}
            controls={false}
            autoPlay={false}

          />
          {/* Interaction overlay: click to select video, double-click to edit text */}
          <div
            ref={overlayRef}
            className="absolute inset-0 z-10"
            onPointerDownCapture={(e) => {
              pointerDownRef.current = { x: e.clientX, y: e.clientY };
            }}
            onClick={(e) => {
              // Ignore clicks on corner resize handles
              if ((e.target as HTMLElement).closest("[data-corner]")) return;

              // Ignore clicks inside the inline text editor
              if ((e.target as HTMLElement).closest("[data-inline-editor]")) return;

              // Detect drag (moved > 5px) — skip selection change
              const down = pointerDownRef.current;
              if (down) {
                const dist = Math.hypot(e.clientX - down.x, e.clientY - down.y);
                if (dist > 5) return;
              }

              // If inline editing, clicking outside exits the editor
              if (inlineEditItemId) {
                setInlineEditItemId(null);
                return;
              }

              const frame = player$.currentFrame.peek();
              const allTracks = editor$.tracks.peek();
              if (!overlayRef.current) return;

              const item = findTopmostItemAtPoint(
                e,
                frame,
                allTracks,
                overlayRef.current,
                compositionWidth,
                compositionHeight
              );
              selectItem(item?.id ?? null);
            }}
            onDoubleClick={(e) => {
              if ((e.target as HTMLElement).closest("[data-corner]")) return;
              const frame = player$.currentFrame.peek();
              const allTracks = editor$.tracks.peek();
              if (!overlayRef.current) return;

              const textItem = findTopmostItemAtPoint(
                e,
                frame,
                allTracks,
                overlayRef.current,
                compositionWidth,
                compositionHeight,
                "text"
              );
              if (textItem) {
                selectItem(textItem.id);
                setInlineEditItemId(textItem.id);
                setInlineEditScale(playerRef.current?.getScale() ?? 1);
                playerRef.current?.pause();
              } else if (inlineEditItemId) {
                setInlineEditItemId(null);
              }
            }}
          >
            {inlineEditItem && (
              <InlineTextEditor
                item={inlineEditItem}
                scale={inlineEditScale}
                onCommit={(newText) => {
                  updateItemProperties(inlineEditItem.id, { text: newText });
                  setInlineEditItemId(null);
                }}
                onCancel={() => setInlineEditItemId(null)}
              />
            )}
            {selectedVideoItem && (
              <VideoOverlayGate
                item={selectedVideoItem}
                onDeselect={handleVideoDeselect}
              />
            )}
            {selectedImageItem && (
              <ImageOverlayGate
                item={selectedImageItem}
                onDeselect={handleImageDeselect}
              />
            )}
          </div>
        </div>
      </div>

      {/* Controls — re-renders on every frame (lightweight, no Player re-render) */}
      <PreviewControls playerRef={playerRef} duration={duration} />
    </div>
  );
}

export const RemotionPreview = observer(RemotionPreviewInner);
