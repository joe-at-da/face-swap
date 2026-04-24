"use client";

import { observable, batch } from "@legendapp/state";
import type { Caption, SubtitleStyle } from "@/types/remotionEditor";

// ─── State ──────────────────────────────────────────────────────────────────

type SubtitleState = {
  /** Captions keyed by timeline item ID */
  captionsByItemId: Record<string, Caption[]>;
  /** Per-item subtitle styles (items without a custom style use DEFAULT_STYLE) */
  styleByItemId: Record<string, SubtitleStyle>;
  /** IDs of items currently generating subtitles */
  generatingItemIds: string[];
  /** Index of caption being edited (in the SubtitlesTab list) */
  editingCaptionIndex: number | null;
};

export const DEFAULT_STYLE: SubtitleStyle = {
  fontSize: 42,
  fontFamily: "Inter",
  color: "#ffffff",
  highlightColor: "#facc15", // yellow for active word
  highlightEnabled: true,
  backgroundColor: "rgba(0, 0, 0, 0.6)",
  position: "bottom",
  maxWordsPerLine: 6,
  outlineColor: "#000000",
  outlineWidth: 2,
};

export const subtitle$ = observable<SubtitleState>({
  captionsByItemId: {},
  styleByItemId: {},
  generatingItemIds: [],
  editingCaptionIndex: null,
});

// ─── Actions ────────────────────────────────────────────────────────────────

/** Set captions for a specific timeline item. */
export function setCaptions(itemId: string, captions: Caption[]) {
  subtitle$.captionsByItemId[itemId].set(captions);
}

/** Get captions for a specific timeline item. */
export function getCaptions(itemId: string): Caption[] {
  return subtitle$.captionsByItemId[itemId]?.peek() ?? [];
}

/** Remove captions for an item (e.g. when item is deleted). */
export function removeCaptions(itemId: string) {
  subtitle$.captionsByItemId[itemId].delete();
}

/** Update a single caption's text (for inline editing). */
export function updateCaptionText(
  itemId: string,
  captionIndex: number,
  newText: string
) {
  const captions = subtitle$.captionsByItemId[itemId]?.peek();
  if (!captions || captionIndex < 0 || captionIndex >= captions.length) return;

  const updated = [...captions];
  updated[captionIndex] = { ...updated[captionIndex], text: newText };
  subtitle$.captionsByItemId[itemId].set(updated);
}

/** Delete a single caption by index. */
export function deleteCaption(itemId: string, captionIndex: number) {
  const captions = subtitle$.captionsByItemId[itemId]?.peek();
  if (!captions || captionIndex < 0 || captionIndex >= captions.length) return;

  subtitle$.captionsByItemId[itemId].set(
    captions.filter((_, i) => i !== captionIndex)
  );
}

/** Get style for a specific item, falling back to DEFAULT_STYLE. */
export function getItemStyle(itemId: string): SubtitleStyle {
  return subtitle$.styleByItemId[itemId]?.peek() ?? { ...DEFAULT_STYLE };
}

/** Update subtitle style for a specific item. */
export function updateItemSubtitleStyle(itemId: string, updates: Partial<SubtitleStyle>) {
  const current = subtitle$.styleByItemId[itemId]?.peek() ?? { ...DEFAULT_STYLE };
  subtitle$.styleByItemId[itemId].set({ ...current, ...updates });
}

/** Mark an item as generating subtitles. */
export function setGenerating(itemId: string, generating: boolean) {
  const current = subtitle$.generatingItemIds.peek();
  if (generating) {
    if (!current.includes(itemId)) {
      subtitle$.generatingItemIds.set([...current, itemId]);
    }
  } else {
    subtitle$.generatingItemIds.set(current.filter((id) => id !== itemId));
  }
}

/** Check if an item is currently generating subtitles. */
export function isGenerating(itemId: string): boolean {
  return subtitle$.generatingItemIds.peek().includes(itemId);
}

// ─── Timing Sync ────────────────────────────────────────────────────────────

/**
 * Adjust caption timing when a clip is trimmed.
 * Removes captions outside the new range.
 */
export function syncCaptionsOnTrim(
  itemId: string,
  newStartMs: number,
  newEndMs: number
) {
  const captions = subtitle$.captionsByItemId[itemId]?.peek();
  if (!captions) return;

  const filtered = captions.filter(
    (c) => c.startMs >= newStartMs && c.endMs <= newEndMs
  );
  const offset = newStartMs;
  const adjusted = filtered.map((c) => ({
    ...c,
    startMs: c.startMs - offset,
    endMs: c.endMs - offset,
    timestampMs: c.timestampMs != null ? c.timestampMs - offset : null,
  }));
  subtitle$.captionsByItemId[itemId].set(adjusted);
}

/**
 * Adjust caption timing when playback speed changes.
 * Scales relative to the old rate: newTime = oldTime * (oldRate / newRate).
 */
export function syncCaptionsOnSpeedChange(
  itemId: string,
  oldPlaybackRate: number,
  newPlaybackRate: number
) {
  const captions = subtitle$.captionsByItemId[itemId]?.peek();
  if (!captions || newPlaybackRate <= 0 || oldPlaybackRate <= 0) return;

  const ratio = oldPlaybackRate / newPlaybackRate;
  const adjusted = captions.map((c) => ({
    ...c,
    startMs: c.startMs * ratio,
    endMs: c.endMs * ratio,
    timestampMs: c.timestampMs != null ? c.timestampMs * ratio : null,
  }));
  subtitle$.captionsByItemId[itemId].set(adjusted);
}

/**
 * Split captions when a clip is split at a given time.
 * Returns captions for the first and second halves.
 */
export function splitCaptions(
  itemId: string,
  splitAtMs: number,
  newSecondItemId: string
) {
  const captions = subtitle$.captionsByItemId[itemId]?.peek();
  if (!captions) return;

  const firstHalf = captions.filter((c) => c.endMs <= splitAtMs);
  const secondHalf = captions
    .filter((c) => c.startMs >= splitAtMs)
    .map((c) => ({
      ...c,
      startMs: c.startMs - splitAtMs,
      endMs: c.endMs - splitAtMs,
      timestampMs: c.timestampMs != null ? c.timestampMs - splitAtMs : null,
    }));

  batch(() => {
    subtitle$.captionsByItemId[itemId].set(firstHalf);
    subtitle$.captionsByItemId[newSecondItemId].set(secondHalf);
  });

  // Copy subtitle style to the second item if the first has one
  const firstStyle = subtitle$.styleByItemId[itemId]?.peek();
  if (firstStyle) {
    subtitle$.styleByItemId[newSecondItemId].set({ ...firstStyle });
  }
}

// ─── Reset ──────────────────────────────────────────────────────────────────

export function resetSubtitleStore() {
  batch(() => {
    subtitle$.captionsByItemId.set({});
    subtitle$.styleByItemId.set({});
    subtitle$.generatingItemIds.set([]);
    subtitle$.editingCaptionIndex.set(null);
  });
}
