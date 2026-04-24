/**
 * Zod validation schema for Remotion composition JSON.
 *
 * IMPORTANT: Uses zod-v3 (Zod 3.23.8) for Remotion compatibility.
 * The main project uses Zod v4 — do NOT import from "zod" here.
 *
 * This schema serves as a SECURITY GATE — all numeric fields have
 * .max() bounds to prevent abuse via oversized payloads.
 */
import { z } from "zod-v3";

// ─── Constants ───────────────────────────────────────────────────────────────

const MAX_DURATION_FRAMES = 108_000; // 1 hour at 30fps
const MAX_SOURCE_VIDEO_FRAMES = 2_592_000; // 24 hours at 30fps
const MAX_TRACKS = 20;
const MAX_ITEMS_PER_TRACK = 200;
const MAX_TRANSITIONS_PER_TRACK = 199;
const MAX_CAPTIONS = 10_000;
const MAX_TEXT_LENGTH = 1_000;
const MAX_URL_LENGTH = 2_048;

// ─── Shared Schemas ──────────────────────────────────────────────────────────

const cropRectSchema = z.object({
  x: z.number().min(0).max(3840),
  y: z.number().min(0).max(3840),
  width: z.number().min(1).max(3840),
  height: z.number().min(1).max(3840),
});

const itemTransformSchema = z.object({
  scale: z.number().min(0.01).max(10).optional(),
  translateX: z.number().min(-3840).max(3840).optional(),
  translateY: z.number().min(-3840).max(3840).optional(),
  rotation: z.number().min(-360).max(360).optional(),
  cropRect: cropRectSchema.optional(),
});

const keyframeSchema = z.object({
  frame: z.number().int().min(0).max(MAX_DURATION_FRAMES),
  transform: itemTransformSchema,
});

const videoFiltersSchema = z.object({
  brightness: z.number().min(0).max(2).optional(),
  contrast: z.number().min(0).max(2).optional(),
  saturation: z.number().min(0).max(2).optional(),
});

const fitModeSchema = z.enum(["cover", "contain", "fill"]);

const textAnimationSchema = z.enum([
  "none",
  "fade-in",
  "slide-in-left",
  "slide-in-right",
  "typewriter",
]);

const sourceClipMetaSchema = z.object({
  clipId: z.string().uuid(),
  originalStartMs: z.number().min(0).max(86_400_000), // 24 hours in ms
  originalEndMs: z.number().min(0).max(86_400_000),
  sessionDurationMs: z.number().min(0).max(86_400_000),
  mpName: z.string().max(200),
  transcript: z.string().max(50_000),
  thumbnailUrl: z.string().max(MAX_URL_LENGTH).nullable(),
});

// ─── Timeline Item ───────────────────────────────────────────────────────────

const timelineItemSchema = z.object({
  id: z.string().max(100),
  type: z.enum(["video", "text", "image"]),
  from: z.number().int().min(0).max(MAX_DURATION_FRAMES),
  durationInFrames: z.number().int().min(1).max(MAX_DURATION_FRAMES),

  // Video-specific
  src: z.string().max(MAX_URL_LENGTH).optional(),
  startFrom: z.number().int().min(0).max(MAX_SOURCE_VIDEO_FRAMES).optional(),
  endAt: z.number().int().min(0).max(MAX_SOURCE_VIDEO_FRAMES).optional(),
  playbackRate: z.number().min(0.25).max(4).optional(),
  volume: z.number().min(0).max(1).optional(),
  isMuted: z.boolean().optional(),

  // Source clip metadata
  sourceClip: sourceClipMetaSchema.optional(),

  // Visual adjustments
  opacity: z.number().min(0).max(1).optional(),
  filters: videoFiltersSchema.optional(),
  flipH: z.boolean().optional(),
  flipV: z.boolean().optional(),
  fitMode: fitModeSchema.optional(),
  audioFadeIn: z.number().int().min(0).max(300).optional(), // Max 10s at 30fps
  audioFadeOut: z.number().int().min(0).max(300).optional(),

  // Transform
  transform: itemTransformSchema.optional(),
  keyframes: z.array(keyframeSchema).max(100).optional(),

  // Text-specific
  text: z.string().max(MAX_TEXT_LENGTH).optional(),
  fontSize: z.number().min(8).max(500).optional(),
  fontFamily: z.string().max(100).optional(),
  color: z.string().max(50).optional(),
  backgroundColor: z.string().max(50).optional(),
  position: z
    .object({
      x: z.number().min(-3840).max(3840),
      y: z.number().min(-3840).max(3840),
    })
    .optional(),
  animation: textAnimationSchema.optional(),

  // Image-specific
  imageWidthPercent: z.number().min(5).max(100).optional(),
});

// ─── Transition ──────────────────────────────────────────────────────────────

const transitionSchema = z.object({
  id: z.string().max(100),
  type: z.enum(["fade", "slide", "wipe", "crossfade", "flip", "clock-wipe"]),
  durationInFrames: z.number().int().min(1).max(300), // Max 10 seconds at 30fps
  timing: z.enum(["linear", "spring"]),
  direction: z
    .enum(["from-left", "from-right", "from-top", "from-bottom"])
    .optional(),
  afterItemId: z.string().max(100),
  beforeItemId: z.string().max(100),
});

// ─── Track ───────────────────────────────────────────────────────────────────

const trackSchema = z.object({
  id: z.string().max(100),
  name: z.string().max(100),
  type: z.enum(["video", "text", "audio", "generic"]),
  items: z.array(timelineItemSchema).max(MAX_ITEMS_PER_TRACK),
  transitions: z.array(transitionSchema).max(MAX_TRANSITIONS_PER_TRACK),
});

// ─── Subtitles ───────────────────────────────────────────────────────────────

const captionSchema = z.object({
  text: z.string().max(MAX_TEXT_LENGTH),
  startMs: z.number().min(0).max(86_400_000),
  endMs: z.number().min(0).max(86_400_000),
  timestampMs: z.number().min(0).max(86_400_000).nullable(),
  confidence: z.number().min(0).max(1).nullable(),
});

const subtitleStyleSchema = z.object({
  fontSize: z.number().min(8).max(200),
  fontFamily: z.string().max(100),
  color: z.string().max(50),
  highlightColor: z.string().max(50),
  highlightEnabled: z.boolean().optional(),
  backgroundColor: z.string().max(50),
  position: z.enum(["bottom", "center", "top"]),
  maxWordsPerLine: z.number().int().min(1).max(20),
  outlineColor: z.string().max(50).optional(),
  outlineWidth: z.number().min(0).max(20).optional(),
  shadowColor: z.string().max(50).optional().nullable(),
  shadowBlur: z.number().min(0).max(50).optional().nullable(),
});

const subtitleTrackSchema = z.object({
  captions: z.array(captionSchema).max(MAX_CAPTIONS),
  style: subtitleStyleSchema,
});

// ─── Metadata ────────────────────────────────────────────────────────────────

const metadataSchema = z.object({
  clipId: z.string().uuid(),
  userId: z.string().uuid(),
  teamId: z.string().uuid().nullable(),
  createdAt: z.string().max(50),
  outputFormat: z.enum(["landscape", "vertical"]),
});

// ─── Root Composition ────────────────────────────────────────────────────────

export const videoCompositionSchema = z.object({
  version: z.literal(2),
  fps: z.literal(30),
  width: z.number().int().min(1).max(3840),
  height: z.number().int().min(1).max(3840),
  durationInFrames: z.number().int().min(1).max(MAX_DURATION_FRAMES),

  tracks: z.array(trackSchema).min(1).max(MAX_TRACKS),
  subtitles: subtitleTrackSchema.nullable(),

  metadata: metadataSchema,
});

export type VideoCompositionSchema = z.infer<typeof videoCompositionSchema>;

// Re-export sub-schemas for individual validation
export {
  timelineItemSchema,
  trackSchema,
  transitionSchema,
  subtitleTrackSchema,
  metadataSchema,
};
