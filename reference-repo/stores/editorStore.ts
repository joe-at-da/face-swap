"use client";

import { observable, batch } from "@legendapp/state";
import { nanoid } from "nanoid";
import type {
  Track,
  TimelineItem,
  CanvasMode,
  VideoComposition,
  EditorCommand,
  SubtitleTrack,
} from "@/types/remotionEditor";
import {
  syncCaptionsOnSpeedChange,
  syncCaptionsOnTrim,
  splitCaptions,
  subtitle$,
  removeCaptions,
} from "@/stores/subtitleStore";

import { EDITOR_FPS } from "@/lib/editorConstants";

// ─── Constants ───────────────────────────────────────────────────────────────

const MAX_UNDO_STACK = 50;
const AUTO_SAVE_DEBOUNCE_MS = 2000;

// ─── State Types ─────────────────────────────────────────────────────────────

type EditorStoreState = {
  tracks: Track[];
  selectedItemId: string | null;
  selectedTrackId: string | null;
  totalDurationInFrames: number;
  canvasMode: CanvasMode;
  snapEnabled: boolean;
  snapIndicatorFrame: number | null;
  zoomLevel: number; // pixels per second

  // Undo/Redo
  undoStack: EditorCommand[];
  redoStack: EditorCommand[];

  // Metadata
  clipId: string | null;
  userId: string | null;
  teamId: string | null;

  // Draft state
  isDirty: boolean;
  lastSavedAt: number | null;
};

// ─── Store ───────────────────────────────────────────────────────────────────

export const editor$ = observable<EditorStoreState>({
  tracks: [
    {
      id: "track-video-0",
      name: "Video 1",
      type: "video",
      items: [],
      transitions: [],
    },
  ],
  selectedItemId: null,
  selectedTrackId: null,
  totalDurationInFrames: 0,
  canvasMode: "landscape",
  snapEnabled: true,
  snapIndicatorFrame: null,
  zoomLevel: 100,

  undoStack: [],
  redoStack: [],

  clipId: null,
  userId: null,
  teamId: null,

  isDirty: false,
  lastSavedAt: null,
});

// ─── Auto-save ───────────────────────────────────────────────────────────────

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    saveToLocalStorage();
  }, AUTO_SAVE_DEBOUNCE_MS);
}

/** Synchronous flush for beforeunload handler */
export function flushSave() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = null;
  }
  if (editor$.isDirty.peek()) {
    saveToLocalStorage();
  }
}

function saveToLocalStorage() {
  const clipId = editor$.clipId.peek();
  if (!clipId) return;

  const state = editor$.peek();
  const subtitleState = subtitle$.peek();
  const saveData = {
    tracks: state.tracks,
    canvasMode: state.canvasMode,
    captionsByItemId: subtitleState.captionsByItemId,
    styleByItemId: subtitleState.styleByItemId,
    savedAt: Date.now(),
  };

  try {
    localStorage.setItem(
      `remotion-editor-${clipId}`,
      JSON.stringify(saveData)
    );
    editor$.isDirty.set(false);
    editor$.lastSavedAt.set(Date.now());
  } catch {
    // localStorage quota exceeded — silently fail
  }
}

/** Load draft from localStorage. Returns true if draft was restored. */
export function loadFromLocalStorage(clipId: string): boolean {
  try {
    const raw = localStorage.getItem(`remotion-editor-${clipId}`);
    if (!raw) return false;

    const data = JSON.parse(raw);
    if (!data?.tracks || !Array.isArray(data.tracks)) return false;

    batch(() => {
      editor$.tracks.set(data.tracks);
      if (data.canvasMode) editor$.canvasMode.set(data.canvasMode);
      editor$.lastSavedAt.set(data.savedAt ?? null);
      editor$.isDirty.set(false);
      recalculateTotalDuration();
    });

    // Restore subtitle data if present
    if (data.captionsByItemId && typeof data.captionsByItemId === "object") {
      subtitle$.captionsByItemId.set(data.captionsByItemId);
    }
    if (data.styleByItemId && typeof data.styleByItemId === "object") {
      subtitle$.styleByItemId.set(data.styleByItemId);
    }

    return true;
  } catch {
    return false;
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function markDirty() {
  editor$.isDirty.set(true);
  scheduleAutoSave();
}

function recalculateTotalDuration() {
  const tracks = editor$.tracks.peek();
  let maxFrame = 0;
  for (const track of tracks) {
    for (const item of track.items) {
      const end = item.from + item.durationInFrames;
      if (end > maxFrame) maxFrame = end;
    }
  }
  editor$.totalDurationInFrames.set(maxFrame);
}

/**
 * Find an item by ID across all tracks, returning the item and its track info.
 * Replaces the 6x duplicated item-lookup loop pattern.
 */
function findItemWithTrack(
  itemId: string
): { item: TimelineItem; trackId: string; trackIndex: number } | null {
  const tracks = editor$.tracks.peek();
  for (let ti = 0; ti < tracks.length; ti++) {
    const found = tracks[ti].items.find((i) => i.id === itemId);
    if (found) {
      return { item: found, trackId: tracks[ti].id, trackIndex: ti };
    }
  }
  return null;
}

/**
 * Resolve the current index of a track by its stable ID.
 * Used in undo/redo closures where trackIndex may have changed.
 */
function resolveTrackIndex(trackId: string): number {
  return editor$.tracks.peek().findIndex((t) => t.id === trackId);
}

// ─── Overlap Detection ───────────────────────────────────────────────────────

/**
 * Check if placing an item at [from, from+duration) would overlap
 * any existing items on the given items array.
 */
function hasOverlap(
  items: TimelineItem[],
  from: number,
  duration: number,
  excludeItemId?: string
): boolean {
  const end = from + duration;
  return items.some((other) => {
    if (excludeItemId && other.id === excludeItemId) return false;
    const otherEnd = other.from + other.durationInFrames;
    return from < otherEnd && end > other.from;
  });
}

/**
 * Find a track where an item can be inserted at [insertAt, insertAt+duration)
 * without overlapping existing items.
 *
 * Priority: preferredTrack → other existing tracks → auto-create new track.
 */
function findNonOverlappingTrack(
  preferredTrack: Track,
  insertAt: number,
  duration: number
): { track: Track; wasCreated: boolean } {
  // 1. Try preferred track
  if (!hasOverlap(preferredTrack.items, insertAt, duration)) {
    return { track: preferredTrack, wasCreated: false };
  }

  // 2. Try other existing tracks
  const tracks = editor$.tracks.peek();
  for (const t of tracks) {
    if (t.id === preferredTrack.id) continue;
    if (!hasOverlap(t.items, insertAt, duration)) {
      return { track: t, wasCreated: false };
    }
  }

  // 3. All tracks overlap — create a new track
  const newTrack: Track = {
    id: `track-${nanoid(6)}`,
    name: `Track ${tracks.length + 1}`,
    type: "generic",
    items: [],
    transitions: [],
  };
  editor$.tracks.set([...tracks, newTrack]);
  return { track: newTrack, wasCreated: true };
}

// ─── Undo/Redo ───────────────────────────────────────────────────────────────

function pushCommand(command: EditorCommand) {
  const stack = editor$.undoStack.peek();
  const newStack =
    stack.length >= MAX_UNDO_STACK ? stack.slice(1) : [...stack];
  newStack.push(command);
  editor$.undoStack.set(newStack);
  editor$.redoStack.set([]); // Clear redo on new action
}

export function undo() {
  const stack = editor$.undoStack.peek();
  if (stack.length === 0) return;

  const command = stack[stack.length - 1];
  command.undo();

  editor$.undoStack.set(stack.slice(0, -1));
  editor$.redoStack.set([...editor$.redoStack.peek(), command]);
  markDirty();
}

export function redo() {
  const stack = editor$.redoStack.peek();
  if (stack.length === 0) return;

  const command = stack[stack.length - 1];
  command.execute();

  editor$.redoStack.set(stack.slice(0, -1));
  editor$.undoStack.set([...editor$.undoStack.peek(), command]);
  markDirty();
}


// ─── Track Operations ────────────────────────────────────────────────────────

export function initializeEditor(
  clipId: string,
  userId: string,
  teamId: string | null
) {
  batch(() => {
    editor$.clipId.set(clipId);
    editor$.userId.set(userId);
    editor$.teamId.set(teamId);
  });
}

/**
 * Add a video clip item to a video track.
 * If targetTrackId is specified, inserts into that track.
 * Otherwise inserts into the last video track.
 * Appends after the last item (or at frame 0 if empty).
 */
export function addVideoItem(params: {
  src: string;
  clipId: string;
  startTimestamp: string;
  endTimestamp: string;
  sessionDurationMs: number;
  mpName: string;
  transcript: string;
  thumbnailUrl: string | null;
  durationSeconds: number;
  targetTrackId?: string;
}): TimelineItem {
  const tracks = editor$.tracks.peek();
  const videoTrack = params.targetTrackId
    ? tracks.find((t) => t.id === params.targetTrackId) ?? tracks[tracks.length - 1]
    : tracks[tracks.length - 1];
  if (!videoTrack) throw new Error("No track found");

  // Find the next available position (after last item on the track)
  let insertFrom = 0;
  for (const item of videoTrack.items) {
    const end = item.from + item.durationInFrames;
    if (end > insertFrom) insertFrom = end;
  }

  const durationInFrames = Math.round(params.durationSeconds * EDITOR_FPS);
  const startMs = parseTimestampToMs(params.startTimestamp);
  const endMs = parseTimestampToMs(params.endTimestamp);

  const newItem: TimelineItem = {
    id: nanoid(),
    type: "video",
    from: insertFrom,
    durationInFrames,
    src: params.src,
    startFrom: Math.round((startMs / 1000) * EDITOR_FPS),
    endAt: Math.round((endMs / 1000) * EDITOR_FPS),
    playbackRate: 1,
    volume: 1,
    isMuted: false,
    sourceClip: {
      clipId: params.clipId,
      originalStartMs: startMs,
      originalEndMs: endMs,
      sessionDurationMs: params.sessionDurationMs,
      mpName: params.mpName,
      transcript: params.transcript,
      thumbnailUrl: params.thumbnailUrl,
    },
  };

  // Capture state for undo
  const prevItems = [...videoTrack.items];

  batch(() => {
    const trackIndex = editor$.tracks
      .peek()
      .findIndex((t) => t.id === videoTrack.id);
    editor$.tracks[trackIndex].items.set([...prevItems, newItem]);
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "addVideoItem",
    description: `Add clip: ${params.mpName}`,
    execute: () => {
      const idx = editor$.tracks
        .peek()
        .findIndex((t) => t.id === videoTrack.id);
      editor$.tracks[idx].items.set([...prevItems, newItem]);
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      const idx = editor$.tracks
        .peek()
        .findIndex((t) => t.id === videoTrack.id);
      editor$.tracks[idx].items.set(prevItems);
      recalculateTotalDuration();
      markDirty();
    },
  });

  return newItem;
}

/**
 * Add a text overlay item to a track.
 * Uses selected track if available, otherwise last track.
 * Creates a track if none exists.
 */
export function addTextItem(params: {
  text: string;
  fontSize?: number;
  fontFamily?: string;
  color?: string;
  backgroundColor?: string;
  animation?: TimelineItem["animation"];
  position?: { x: number; y: number };
  insertAtFrame?: number;
  durationInFrames?: number;
}): TimelineItem {
  const tracks = editor$.tracks.peek();
  const selectedTrackId = editor$.selectedTrackId.peek();

  // Determine preferred target track (selected > last > null)
  let preferredTrack = selectedTrackId
    ? tracks.find((t) => t.id === selectedTrackId) ?? null
    : null;
  if (!preferredTrack && tracks.length > 0) {
    preferredTrack = tracks[tracks.length - 1];
  }

  const insertAt = params.insertAtFrame ?? 0;
  const duration = params.durationInFrames ?? EDITOR_FPS * 3; // default 3 seconds

  // Find a track without overlap (may auto-create one)
  let targetTrack: Track;
  let wasCreated: boolean;
  if (preferredTrack) {
    ({ track: targetTrack, wasCreated } = findNonOverlappingTrack(
      preferredTrack,
      insertAt,
      duration
    ));
  } else {
    // No tracks at all — create one
    targetTrack = {
      id: `track-${nanoid(6)}`,
      name: "Track 1",
      type: "generic",
      items: [],
      transitions: [],
    };
    editor$.tracks.set([...tracks, targetTrack]);
    wasCreated = true;
  }

  const newItem: TimelineItem = {
    id: nanoid(),
    type: "text",
    from: insertAt,
    durationInFrames: duration,
    text: params.text,
    fontSize: params.fontSize ?? 48,
    fontFamily: params.fontFamily ?? "Inter",
    color: params.color ?? "#ffffff",
    backgroundColor: params.backgroundColor ?? "transparent",
    animation: params.animation ?? "none",
    position: params.position ?? { x: 0.5, y: 0.8 }, // center-bottom
  };

  const prevItems = [...targetTrack.items];
  const targetTrackId = targetTrack.id;
  // Capture pre-insertion track list for undo of auto-created tracks
  const prevTracks = wasCreated
    ? editor$.tracks.peek().filter((t) => t.id !== targetTrackId)
    : null;

  batch(() => {
    const idx = resolveTrackIndex(targetTrackId);
    editor$.tracks[idx].items.set([...prevItems, newItem]);
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "addTextItem",
    description: `Add text: "${params.text.slice(0, 20)}"`,
    execute: () => {
      if (wasCreated && resolveTrackIndex(targetTrackId) === -1) {
        const currentTracks = editor$.tracks.peek();
        editor$.tracks.set([
          ...currentTracks,
          { ...targetTrack, items: [newItem] },
        ]);
      } else {
        const idx = resolveTrackIndex(targetTrackId);
        editor$.tracks[idx].items.set([...prevItems, newItem]);
      }
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      if (wasCreated && prevTracks) {
        editor$.tracks.set(prevTracks);
      } else {
        const idx = resolveTrackIndex(targetTrackId);
        editor$.tracks[idx].items.set(prevItems);
      }
      recalculateTotalDuration();
      markDirty();
    },
  });

  return newItem;
}

/**
 * Add an image overlay item to a track.
 * Uses selected track if available, otherwise last track.
 * Creates a track if none exists.
 */
export function addImageItem(params: {
  src: string;
  imageWidthPercent?: number;
  position?: { x: number; y: number };
  animation?: TimelineItem["animation"];
  insertAtFrame?: number;
  durationInFrames?: number;
  opacity?: number;
  fitMode?: TimelineItem["fitMode"];
}): TimelineItem {
  const tracks = editor$.tracks.peek();
  const selectedTrackId = editor$.selectedTrackId.peek();

  // Determine preferred target track (selected > last > null)
  let preferredTrack = selectedTrackId
    ? tracks.find((t) => t.id === selectedTrackId) ?? null
    : null;
  if (!preferredTrack && tracks.length > 0) {
    preferredTrack = tracks[tracks.length - 1];
  }

  const insertAt = params.insertAtFrame ?? 0;
  const duration = params.durationInFrames ?? EDITOR_FPS * 5; // default 5 seconds

  // Find a track without overlap (may auto-create one)
  let targetTrack: Track;
  let wasCreated: boolean;
  if (preferredTrack) {
    ({ track: targetTrack, wasCreated } = findNonOverlappingTrack(
      preferredTrack,
      insertAt,
      duration
    ));
  } else {
    // No tracks at all — create one
    targetTrack = {
      id: `track-${nanoid(6)}`,
      name: "Track 1",
      type: "generic",
      items: [],
      transitions: [],
    };
    editor$.tracks.set([...tracks, targetTrack]);
    wasCreated = true;
  }

  const newItem: TimelineItem = {
    id: nanoid(),
    type: "image",
    from: insertAt,
    durationInFrames: duration,
    src: params.src,
    imageWidthPercent: params.imageWidthPercent ?? 30,
    position: params.position ?? { x: 0.5, y: 0.5 },
    opacity: params.opacity ?? 1,
    fitMode: params.fitMode ?? "contain",
    animation: params.animation ?? "none",
  };

  const prevItems = [...targetTrack.items];
  const targetTrackId = targetTrack.id;
  // Capture pre-insertion track list for undo of auto-created tracks
  const prevTracks = wasCreated
    ? editor$.tracks.peek().filter((t) => t.id !== targetTrackId)
    : null;

  batch(() => {
    const idx = resolveTrackIndex(targetTrackId);
    editor$.tracks[idx].items.set([...prevItems, newItem]);
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "addImageItem",
    description: `Add image`,
    execute: () => {
      if (wasCreated && resolveTrackIndex(targetTrackId) === -1) {
        const currentTracks = editor$.tracks.peek();
        editor$.tracks.set([
          ...currentTracks,
          { ...targetTrack, items: [newItem] },
        ]);
      } else {
        const idx = resolveTrackIndex(targetTrackId);
        editor$.tracks[idx].items.set([...prevItems, newItem]);
      }
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      if (wasCreated && prevTracks) {
        editor$.tracks.set(prevTracks);
      } else {
        const idx = resolveTrackIndex(targetTrackId);
        editor$.tracks[idx].items.set(prevItems);
      }
      recalculateTotalDuration();
      markDirty();
    },
  });

  return newItem;
}

// ─── Track Management ─────────────────────────────────────────────────────────

/**
 * Add a new empty generic track.
 */
export function addTrack(): Track {
  const tracks = editor$.tracks.peek();

  const newTrack: Track = {
    id: `track-${nanoid(6)}`,
    name: `Track ${tracks.length + 1}`,
    type: "generic",
    items: [],
    transitions: [],
  };

  editor$.tracks.set([...tracks, newTrack]);
  markDirty();
  return newTrack;
}

/**
 * Move a track up or down in the track list.
 */
export function reorderTrack(trackId: string, direction: "up" | "down") {
  const tracks = editor$.tracks.peek();
  const index = tracks.findIndex((t) => t.id === trackId);
  if (index === -1) return;

  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= tracks.length) return;

  const newTracks = [...tracks];
  const [moved] = newTracks.splice(index, 1);
  newTracks.splice(targetIndex, 0, moved);
  editor$.tracks.set(newTracks);
  markDirty();
}

/**
 * Remove a track by ID. Cannot remove the last remaining track.
 */
export function removeTrack(trackId: string) {
  const tracks = editor$.tracks.peek();
  const track = tracks.find((t) => t.id === trackId);
  if (!track) return;

  // Prevent removing the last remaining track
  if (tracks.length <= 1) {
    return;
  }

  batch(() => {
    editor$.tracks.set(tracks.filter((t) => t.id !== trackId));
    // Clear selection if selected item was on this track
    const sel = editor$.selectedItemId.peek();
    if (sel && track.items.some((i) => i.id === sel)) {
      editor$.selectedItemId.set(null);
    }
    recalculateTotalDuration();
    markDirty();
  });
}

/**
 * Remove an item from any track.
 */
export function removeItem(itemId: string) {
  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { trackId, trackIndex } = result;
  const prevItems = [...editor$.tracks.peek()[trackIndex].items];

  batch(() => {
    editor$.tracks[trackIndex].items.set(
      prevItems.filter((item) => item.id !== itemId)
    );
    if (editor$.selectedItemId.peek() === itemId) {
      editor$.selectedItemId.set(null);
    }
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "removeItem",
    description: `Remove item`,
    execute: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(
        prevItems.filter((item) => item.id !== itemId)
      );
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(prevItems);
      recalculateTotalDuration();
      markDirty();
    },
  });
}

/**
 * Select a timeline item.
 */
export function selectItem(itemId: string | null) {
  editor$.selectedItemId.set(itemId);
}

/**
 * Select a track as the active target for insertions.
 */
export function selectTrack(trackId: string | null) {
  editor$.selectedTrackId.set(trackId);
}

/**
 * Toggle canvas mode between landscape and vertical.
 */
export function toggleCanvasMode() {
  const current = editor$.canvasMode.peek();
  editor$.canvasMode.set(current === "landscape" ? "vertical" : "landscape");
  markDirty();
}

/**
 * Set zoom level (pixels per second).
 */
export function setZoomLevel(level: number) {
  editor$.zoomLevel.set(Math.max(10, Math.min(500, level)));
}

/**
 * Toggle magnetic snapping.
 */
export function toggleSnap() {
  editor$.snapEnabled.set(!editor$.snapEnabled.peek());
}

// ─── Snap Utilities ─────────────────────────────────────────────────────────

const SNAP_THRESHOLD_FRAMES = 5; // snap within 5 frames (~167ms at 30fps)

/**
 * Collect all snap target frames from the timeline.
 * Targets: item start/end edges (excluding excludeItemId), frame 0.
 * Caller should add playhead frame separately to avoid circular imports.
 */
export function getSnapTargets(excludeItemId: string): number[] {
  const tracks = editor$.tracks.peek();
  const targets: number[] = [0];
  for (const track of tracks) {
    for (const item of track.items) {
      if (item.id === excludeItemId) continue;
      targets.push(item.from);
      targets.push(item.from + item.durationInFrames);
    }
  }
  return targets;
}

/**
 * Snap a frame value to the nearest edge if within the threshold.
 * Returns the snapped frame and which target it snapped to (for visual indicator).
 */
export function snapToEdge(
  frame: number,
  snapTargets: number[]
): { frame: number; snappedTo: number | null } {
  if (!editor$.snapEnabled.peek()) {
    return { frame, snappedTo: null };
  }

  let closestTarget = -1;
  let closestDistance = Infinity;

  for (const target of snapTargets) {
    const distance = Math.abs(frame - target);
    if (distance < closestDistance && distance <= SNAP_THRESHOLD_FRAMES) {
      closestDistance = distance;
      closestTarget = target;
    }
  }

  if (closestTarget >= 0) {
    return { frame: closestTarget, snappedTo: closestTarget };
  }

  return { frame, snappedTo: null };
}

let snapIndicatorTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Show a snap indicator line at the given frame for a brief duration.
 * Pass null to clear immediately.
 */
export function showSnapIndicator(frame: number | null) {
  if (snapIndicatorTimer) {
    clearTimeout(snapIndicatorTimer);
    snapIndicatorTimer = null;
  }

  editor$.snapIndicatorFrame.set(frame);

  if (frame !== null) {
    snapIndicatorTimer = setTimeout(() => {
      editor$.snapIndicatorFrame.set(null);
      snapIndicatorTimer = null;
    }, 500);
  }
}

// ─── Item Operations ────────────────────────────────────────────────────────

/**
 * Move an item to a new position (frame) on the same or different track.
 */
export function moveItem(
  itemId: string,
  newFrom: number,
  newTrackId?: string
) {
  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { item, trackId: sourceTrackId, trackIndex: sourceTrackIndex } = result;
  const tracks = editor$.tracks.peek();
  const targetTrackId = newTrackId ?? sourceTrackId;
  const targetTrackIndex = tracks.findIndex((t) => t.id === targetTrackId);
  if (targetTrackIndex === -1) return;

  const clampedFrom = Math.max(0, Math.round(newFrom));

  if (hasOverlap(tracks[targetTrackIndex].items, clampedFrom, item.durationInFrames, itemId)) return;

  const prevSourceItems = [...tracks[sourceTrackIndex].items];
  const prevTargetItems =
    sourceTrackIndex === targetTrackIndex
      ? prevSourceItems
      : [...tracks[targetTrackIndex].items];
  const isSameTrack = sourceTrackId === targetTrackId;

  batch(() => {
    if (isSameTrack) {
      editor$.tracks[sourceTrackIndex].items.set(
        prevSourceItems.map((i) =>
          i.id === itemId ? { ...i, from: clampedFrom } : i
        )
      );
    } else {
      editor$.tracks[sourceTrackIndex].items.set(
        prevSourceItems.filter((i) => i.id !== itemId)
      );
      editor$.tracks[targetTrackIndex].items.set([
        ...prevTargetItems,
        { ...item, from: clampedFrom },
      ]);
    }
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "moveItem",
    description: `Move item`,
    execute: () => {
      batch(() => {
        if (isSameTrack) {
          const idx = resolveTrackIndex(sourceTrackId);
          editor$.tracks[idx].items.set(
            prevSourceItems.map((i) =>
              i.id === itemId ? { ...i, from: clampedFrom } : i
            )
          );
        } else {
          const srcIdx = resolveTrackIndex(sourceTrackId);
          const tgtIdx = resolveTrackIndex(targetTrackId);
          editor$.tracks[srcIdx].items.set(
            prevSourceItems.filter((i) => i.id !== itemId)
          );
          editor$.tracks[tgtIdx].items.set([
            ...prevTargetItems,
            { ...item, from: clampedFrom },
          ]);
        }
        recalculateTotalDuration();
        markDirty();
      });
    },
    undo: () => {
      batch(() => {
        const srcIdx = resolveTrackIndex(sourceTrackId);
        editor$.tracks[srcIdx].items.set(prevSourceItems);
        if (!isSameTrack) {
          const tgtIdx = resolveTrackIndex(targetTrackId);
          editor$.tracks[tgtIdx].items.set(prevTargetItems);
        }
        recalculateTotalDuration();
        markDirty();
      });
    },
  });
}

/**
 * Trim or extend an item by adjusting its start or end.
 * direction: "start" adjusts the left edge, "end" adjusts the right edge.
 * deltaFrames: positive = extend, negative = trim.
 */
export function trimItem(
  itemId: string,
  direction: "start" | "end",
  deltaFrames: number
) {
  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { item, trackId, trackIndex } = result;
  const prevItems = [...editor$.tracks.peek()[trackIndex].items];
  let updatedItem: TimelineItem;

  if (direction === "start") {
    // Moving the left edge: adjusts from, startFrom, durationInFrames
    const newFrom = Math.max(0, item.from + deltaFrames);
    const actualDelta = newFrom - item.from;
    const newDuration = item.durationInFrames - actualDelta;
    if (newDuration < 1) return; // minimum 1 frame

    const newStartFrom = (item.startFrom ?? 0) + actualDelta;
    if (newStartFrom < 0) return;

    updatedItem = {
      ...item,
      from: newFrom,
      durationInFrames: newDuration,
      startFrom: newStartFrom,
    };
  } else {
    // Moving the right edge: adjusts durationInFrames and endAt
    const newDuration = item.durationInFrames + deltaFrames;
    if (newDuration < 1) return;

    updatedItem = {
      ...item,
      durationInFrames: newDuration,
      endAt:
        item.endAt != null ? item.endAt + deltaFrames : undefined,
    };
  }

  // Compute source-relative time range for subtitle sync
  const newStartFromMs = ((updatedItem.startFrom ?? 0) / EDITOR_FPS) * 1000;
  const newSourceDuration =
    updatedItem.durationInFrames * (updatedItem.playbackRate || 1);
  const newEndAtMs = newStartFromMs + (newSourceDuration / EDITOR_FPS) * 1000;

  batch(() => {
    editor$.tracks[trackIndex].items.set(
      prevItems.map((i) => (i.id === itemId ? updatedItem : i))
    );
    syncCaptionsOnTrim(itemId, newStartFromMs, newEndAtMs);
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "trimItem",
    description: `Trim item ${direction}`,
    execute: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(
        prevItems.map((i) => (i.id === itemId ? updatedItem : i))
      );
      syncCaptionsOnTrim(itemId, newStartFromMs, newEndAtMs);
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(prevItems);
      const origStartMs = ((item.startFrom ?? 0) / EDITOR_FPS) * 1000;
      const origDuration = item.durationInFrames * (item.playbackRate || 1);
      const origEndMs = origStartMs + (origDuration / EDITOR_FPS) * 1000;
      syncCaptionsOnTrim(itemId, origStartMs, origEndMs);
      recalculateTotalDuration();
      markDirty();
    },
  });
}

/**
 * Split an item at the given frame position (razor tool).
 * Creates two items from one, split at the playhead.
 */
export function splitItem(itemId: string, splitAtFrame: number) {
  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { item, trackId, trackIndex } = result;

  const itemEnd = item.from + item.durationInFrames;
  if (splitAtFrame <= item.from || splitAtFrame >= itemEnd) return;

  const prevItems = [...editor$.tracks.peek()[trackIndex].items];

  const firstDuration = splitAtFrame - item.from;
  const secondDuration = itemEnd - splitAtFrame;
  const firstStartFrom = item.startFrom ?? 0;
  const secondStartFrom = firstStartFrom + firstDuration;

  const firstItem: TimelineItem = {
    ...item,
    durationInFrames: firstDuration,
    endAt:
      item.endAt != null
        ? firstStartFrom + firstDuration
        : undefined,
  };

  const secondItem: TimelineItem = {
    ...item,
    id: nanoid(),
    from: splitAtFrame,
    durationInFrames: secondDuration,
    startFrom: secondStartFrom,
    endAt: item.endAt,
  };

  // Calculate split point in milliseconds for caption splitting
  const splitAtMs = (firstDuration / EDITOR_FPS) * 1000;

  batch(() => {
    editor$.tracks[trackIndex].items.set([
      ...prevItems.filter((i) => i.id !== itemId),
      firstItem,
      secondItem,
    ]);
    recalculateTotalDuration();
    markDirty();
  });

  // Split captions between the two items
  splitCaptions(itemId, splitAtMs, secondItem.id);

  pushCommand({
    id: nanoid(),
    type: "splitItem",
    description: `Split item at frame ${splitAtFrame}`,
    execute: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set([
        ...prevItems.filter((i) => i.id !== itemId),
        firstItem,
        secondItem,
      ]);
      splitCaptions(itemId, splitAtMs, secondItem.id);
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      // Merge second item's captions back into the first
      const firstCaps = subtitle$.captionsByItemId[itemId]?.peek() ?? [];
      const secondCaps = subtitle$.captionsByItemId[secondItem.id]?.peek() ?? [];
      const merged = [
        ...firstCaps,
        ...secondCaps.map((c) => ({
          ...c,
          startMs: c.startMs + splitAtMs,
          endMs: c.endMs + splitAtMs,
          timestampMs: c.timestampMs != null ? c.timestampMs + splitAtMs : null,
        })),
      ];
      subtitle$.captionsByItemId[itemId].set(merged);
      removeCaptions(secondItem.id);

      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(prevItems);
      recalculateTotalDuration();
      markDirty();
    },
  });
}

/**
 * Update an item's properties (speed, volume, muted, etc.).
 */
export function updateItemProperties(
  itemId: string,
  updates: Partial<TimelineItem>
) {
  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { item, trackId, trackIndex } = result;
  const prevItems = [...editor$.tracks.peek()[trackIndex].items];
  const updatedItem = { ...item, ...updates, id: item.id };

  batch(() => {
    editor$.tracks[trackIndex].items.set(
      prevItems.map((i) => (i.id === itemId ? updatedItem : i))
    );
    recalculateTotalDuration();
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "updateItemProperties",
    description: `Update item properties`,
    execute: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(
        prevItems.map((i) => (i.id === itemId ? updatedItem : i))
      );
      recalculateTotalDuration();
      markDirty();
    },
    undo: () => {
      const idx = resolveTrackIndex(trackId);
      editor$.tracks[idx].items.set(prevItems);
      recalculateTotalDuration();
      markDirty();
    },
  });
}

/**
 * Update an item's playback speed with automatic duration recalculation
 * and subtitle timing sync.
 */
export function updateItemSpeed(itemId: string, newPlaybackRate: number) {
  if (newPlaybackRate <= 0 || newPlaybackRate > 4) return;

  const result = findItemWithTrack(itemId);
  if (!result) return;

  const { item, trackId, trackIndex } = result;

  const oldRate = item.playbackRate ?? 1;
  if (oldRate === newPlaybackRate) return;

  // Calculate new duration based on the original source duration
  // originalDuration = currentDuration * currentRate
  const originalDuration = item.durationInFrames * oldRate;
  const newDuration = Math.max(1, Math.round(originalDuration / newPlaybackRate));

  const prevItems = [...editor$.tracks[trackIndex].items.peek()];
  const updatedItem: TimelineItem = {
    ...item,
    playbackRate: newPlaybackRate,
    durationInFrames: newDuration,
  };

  batch(() => {
    const idx = resolveTrackIndex(trackId);
    editor$.tracks[idx].items.set(
      prevItems.map((i) => (i.id === itemId ? updatedItem : i))
    );
    recalculateTotalDuration();
    // Sync subtitle timing proportionally
    syncCaptionsOnSpeedChange(itemId, oldRate, newPlaybackRate);
    markDirty();
  });

  pushCommand({
    id: nanoid(),
    type: "updateItemSpeed",
    description: `Change speed to ${newPlaybackRate}x`,
    execute: () => {
      batch(() => {
        const idx = resolveTrackIndex(trackId);
        editor$.tracks[idx].items.set(
          prevItems.map((i) => (i.id === itemId ? updatedItem : i))
        );
        recalculateTotalDuration();
        syncCaptionsOnSpeedChange(itemId, oldRate, newPlaybackRate);
        markDirty();
      });
    },
    undo: () => {
      batch(() => {
        const idx = resolveTrackIndex(trackId);
        editor$.tracks[idx].items.set(prevItems);
        recalculateTotalDuration();
        syncCaptionsOnSpeedChange(itemId, newPlaybackRate, oldRate);
        markDirty();
      });
    },
  });
}

/**
 * Read the current item from the store by ID (non-reactive peek).
 * Useful in event handlers to avoid stale closure issues.
 */
export function peekItem(itemId: string): TimelineItem | undefined {
  for (const track of editor$.tracks.peek()) {
    const found = track.items.find((i) => i.id === itemId);
    if (found) return found;
  }
  return undefined;
}

/**
 * Find the item at a given frame on any track.
 * Used for "split at playhead" to determine which item to split.
 */
export function findItemAtFrame(frame: number): TimelineItem | null {
  const tracks = editor$.tracks.peek();
  for (const track of tracks) {
    for (const item of track.items) {
      if (frame >= item.from && frame < item.from + item.durationInFrames) {
        return item;
      }
    }
  }
  return null;
}

/**
 * Find ALL items that span a given frame across all tracks.
 * Returns items ordered by track index (top → bottom).
 */
export function findAllItemsAtFrame(frame: number): TimelineItem[] {
  const tracks = editor$.tracks.peek();
  const results: TimelineItem[] = [];
  for (const track of tracks) {
    for (const item of track.items) {
      if (frame >= item.from && frame < item.from + item.durationInFrames) {
        results.push(item);
      }
    }
  }
  return results;
}

/**
 * Resolve which item should be the target of a playhead-based action.
 * Priority:
 * 1. If selectedItemId is set and the playhead is within that item → use it.
 * 2. Otherwise → first item at playhead (top track wins).
 */
export function resolveTargetItem(frame: number): TimelineItem | null {
  const selectedId = editor$.selectedItemId.peek();

  if (selectedId) {
    const tracks = editor$.tracks.peek();
    for (const track of tracks) {
      const item = track.items.find((i) => i.id === selectedId);
      if (
        item &&
        frame > item.from &&
        frame < item.from + item.durationInFrames
      ) {
        return item;
      }
    }
  }

  return findItemAtFrame(frame);
}

// ─── Composition JSON Derivation ─────────────────────────────────────────────

/**
 * Derive the full VideoComposition JSON from current editor state.
 * This is what gets sent to RunPod for rendering.
 */
export function getCompositionJSON(
  subtitles: SubtitleTrack | null = null
): VideoComposition {
  const state = editor$.peek();

  if (!state.clipId || !state.userId) {
    throw new Error("Editor not initialized: missing clipId or userId");
  }

  const isLandscape = state.canvasMode === "landscape";

  return {
    version: 2,
    fps: 30,
    width: isLandscape ? 1920 : 1080,
    height: isLandscape ? 1080 : 1920,
    durationInFrames: state.totalDurationInFrames,
    tracks: state.tracks,
    subtitles,
    metadata: {
      clipId: state.clipId,
      userId: state.userId,
      teamId: state.teamId ?? null,
      createdAt: new Date().toISOString(),
      outputFormat: state.canvasMode,
    },
  };
}

// ─── Reset ───────────────────────────────────────────────────────────────────

export function resetEditor() {
  batch(() => {
    editor$.tracks.set([
      {
        id: "track-video-0",
        name: "Video 1",
        type: "video",
        items: [],
        transitions: [],
      },
    ]);
    editor$.selectedItemId.set(null);
    editor$.selectedTrackId.set(null);
    editor$.totalDurationInFrames.set(0);
    editor$.canvasMode.set("landscape");
    editor$.snapEnabled.set(true);
    editor$.snapIndicatorFrame.set(null);
    editor$.zoomLevel.set(100);
    editor$.undoStack.set([]);
    editor$.redoStack.set([]);
    editor$.isDirty.set(false);
    editor$.lastSavedAt.set(null);
  });
}

// ─── Timestamp Utils ─────────────────────────────────────────────────────────

export function parseTimestampToMs(timestamp: string): number {
  const [timePart, msPart] = timestamp.split(".");
  const parts = timePart.split(":");

  if (parts.length === 3) {
    const [hours, minutes, seconds] = parts.map(Number);
    return (
      (hours * 3600 + minutes * 60 + seconds) * 1000 +
      (msPart ? Number(msPart.padEnd(3, "0").slice(0, 3)) : 0)
    );
  }
  const [minutes, seconds] = parts.map(Number);
  return (
    (minutes * 60 + seconds) * 1000 +
    (msPart ? Number(msPart.padEnd(3, "0").slice(0, 3)) : 0)
  );
}
