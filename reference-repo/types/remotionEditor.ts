/**
 * Remotion Video Editor Type Definitions
 *
 * Root composition JSON output sent to RunPod for rendering.
 * All time values are in frames (30fps).
 */

// ─── Root Composition ────────────────────────────────────────────────────────

export interface VideoComposition {
  version: 2;
  fps: 30;
  width: number; // 1920 (landscape) or 1080 (vertical)
  height: number; // 1080 (landscape) or 1920 (vertical)
  durationInFrames: number;

  tracks: Track[];
  subtitles: SubtitleTrack | null;

  metadata: CompositionMetadata;
}

export interface CompositionMetadata {
  clipId: string;
  userId: string;
  teamId: string | null;
  createdAt: string; // ISO 8601
  outputFormat: OutputFormat;
}

export type OutputFormat = "landscape" | "vertical";
export type CanvasMode = "landscape" | "vertical";

// ─── Tracks & Items ──────────────────────────────────────────────────────────

export type TrackType = "video" | "text" | "audio" | "generic";

export interface Track {
  id: string;
  name: string;
  type: TrackType;
  items: TimelineItem[];
  transitions: Transition[];
}

export interface TimelineItem {
  id: string;
  type: "video" | "text" | "image";
  from: number; // Start frame (0-based)
  durationInFrames: number;

  // Video-specific
  src?: string;
  startFrom?: number; // Frame offset into the source video
  endAt?: number; // Frame end in the source video
  playbackRate?: number; // 0.25 - 4.0, default 1
  volume?: number; // 0 - 1, default 1
  isMuted?: boolean;

  // Source clip metadata (for extend/trim limits)
  sourceClip?: SourceClipMeta;

  // Visual adjustments (primarily video)
  opacity?: number; // 0–1, default 1
  filters?: VideoFilters;
  flipH?: boolean;
  flipV?: boolean;
  fitMode?: FitMode;
  audioFadeIn?: number; // frames, default 0
  audioFadeOut?: number; // frames, default 0

  // Transform
  transform?: ItemTransform;
  keyframes?: Keyframe[];

  // Text-specific
  text?: string;
  fontSize?: number;
  fontFamily?: string;
  color?: string;
  backgroundColor?: string;
  position?: { x: number; y: number };
  animation?: TextAnimation;

  // Image-specific
  imageWidthPercent?: number; // 5-100, % of composition width
}

export interface SourceClipMeta {
  clipId: string;
  originalStartMs: number;
  originalEndMs: number;
  sessionDurationMs: number;
  mpName: string;
  transcript: string;
  thumbnailUrl: string | null;
}

// ─── Video Filters & Fit ─────────────────────────────────────────────────────

export interface VideoFilters {
  brightness?: number; // 0–2, default 1
  contrast?: number; // 0–2, default 1
  saturation?: number; // 0–2, default 1
}

export type FitMode = "cover" | "contain" | "fill";

// ─── Transforms & Keyframes ──────────────────────────────────────────────────

export interface ItemTransform {
  scale?: number;
  translateX?: number;
  translateY?: number;
  rotation?: number;
  cropRect?: CropRect;
}

export interface CropRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Keyframe {
  frame: number;
  transform: ItemTransform;
}

export type TextAnimation =
  | "none"
  | "fade-in"
  | "slide-in-left"
  | "slide-in-right"
  | "typewriter";

// ─── Transitions ─────────────────────────────────────────────────────────────

export type TransitionType =
  | "fade"
  | "slide"
  | "wipe"
  | "crossfade"
  | "flip"
  | "clock-wipe";

export type TransitionDirection =
  | "from-left"
  | "from-right"
  | "from-top"
  | "from-bottom";

export interface Transition {
  id: string;
  type: TransitionType;
  durationInFrames: number;
  timing: "linear" | "spring";
  direction?: TransitionDirection;
  afterItemId: string;
  beforeItemId: string;
}

// ─── Subtitles ───────────────────────────────────────────────────────────────

export interface SubtitleTrack {
  captions: Caption[];
  style: SubtitleStyle;
}

export interface Caption {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
}

export interface SubtitleStyle {
  fontSize: number;
  fontFamily: string;
  color: string;
  highlightColor: string;
  highlightEnabled: boolean;
  backgroundColor: string;
  position: "bottom" | "center" | "top";
  maxWordsPerLine: number;
  outlineColor?: string;
  outlineWidth?: number;
  shadowColor?: string;
  shadowBlur?: number;
}

// ─── Editor State Types (not serialized to JSON) ─────────────────────────────

export interface PlayerState {
  isPlaying: boolean;
  currentFrame: number;
  shuttleSpeed: number; // -4, -2, -1, 0, 1, 2, 4
}

// ─── Command Stack (Undo/Redo) ───────────────────────────────────────────────

export interface EditorCommand {
  id: string;
  type: string;
  description: string;
  execute: () => void;
  undo: () => void;
}

// ─── Editor Props (passed from server component) ─────────────────────────────

export interface RemotionEditorProps {
  mpName: string;
  sessionDate: string;
  eventTitle: string | null;
  sessionClips: SessionClipForEditor[];
  mainMpId: number;
  activeClipId: string;
  fullVideoUrl: string | null;
  sessionLengthSeconds: number | null;
  mainClip: MainClipForEditor;
  teamId: string | undefined;
  userId: string;
}

/** Minimal session clip data needed by the editor */
export interface SessionClipForEditor {
  id: string;
  member_id: number;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  start_timestamp: string;
  end_timestamp: string;
  transcript: string;
  description: string | null;
  session_uid: string | null;
  parliament_members: { display_name: string | null } | null;
}

/** Main clip data with full member info */
export interface MainClipForEditor {
  id: string;
  member_id: number;
  session_uid: string | null;
  full_video_path: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  start_timestamp: string;
  end_timestamp: string;
  transcript: string | null;
  description: string | null;
  parliament_members: {
    member_id: number;
    display_name: string | null;
    party_name: string | null;
    party_abbreviation: string | null;
    party_background_colour: string | null;
    party_foreground_colour: string | null;
  };
}
