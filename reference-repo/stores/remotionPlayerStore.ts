"use client";

import { observable } from "@legendapp/state";
import type { PlayerState } from "@/types/remotionEditor";

// ─── Store ───────────────────────────────────────────────────────────────────

export const player$ = observable<PlayerState>({
  isPlaying: false,
  currentFrame: 0,
  shuttleSpeed: 0, // -4, -2, -1, 0, 1, 2, 4
});

// Seek gate: when true, ignore frameupdate events (prevents playhead jitter)
let isSeeking = false;
let seekTimeoutId: ReturnType<typeof setTimeout> | null = null;

// ─── Playback Control ────────────────────────────────────────────────────────

export function setIsPlaying(playing: boolean) {
  player$.isPlaying.set(playing);
}

export function setCurrentFrame(frame: number) {
  if (!isSeeking) {
    player$.currentFrame.set(frame);
  }
}

/**
 * Begin a seek operation. While seeking, frameupdate events are ignored.
 * Auto-resets after 500ms as a safety net if endSeek() is never called.
 */
export function beginSeek() {
  isSeeking = true;
  if (seekTimeoutId) clearTimeout(seekTimeoutId);
  seekTimeoutId = setTimeout(() => {
    isSeeking = false;
    seekTimeoutId = null;
  }, 500);
}

/**
 * End a seek operation. Resume listening to frameupdate events.
 */
export function endSeek() {
  isSeeking = false;
  if (seekTimeoutId) {
    clearTimeout(seekTimeoutId);
    seekTimeoutId = null;
  }
}

// ─── Shuttle Speed (J/K/L) ───────────────────────────────────────────────────

const SHUTTLE_SPEEDS = [-4, -2, -1, 0, 1, 2, 4] as const;

/**
 * Shuttle forward: increase speed (L key behavior).
 * 0 → 1 → 2 → 4
 */
export function shuttleForward() {
  const current = player$.shuttleSpeed.peek();
  const idx = SHUTTLE_SPEEDS.indexOf(
    current as (typeof SHUTTLE_SPEEDS)[number]
  );
  if (idx < SHUTTLE_SPEEDS.length - 1) {
    player$.shuttleSpeed.set(SHUTTLE_SPEEDS[idx + 1]);
  }
}

/**
 * Shuttle backward: decrease speed (J key behavior).
 * 0 → -1 → -2 → -4
 */
export function shuttleBackward() {
  const current = player$.shuttleSpeed.peek();
  const idx = SHUTTLE_SPEEDS.indexOf(
    current as (typeof SHUTTLE_SPEEDS)[number]
  );
  if (idx > 0) {
    player$.shuttleSpeed.set(SHUTTLE_SPEEDS[idx - 1]);
  }
}

/**
 * Stop shuttle / pause (K key behavior).
 */
export function shuttleStop() {
  player$.shuttleSpeed.set(0);
}

// ─── Reset ───────────────────────────────────────────────────────────────────

export function resetPlayerStore() {
  player$.isPlaying.set(false);
  player$.currentFrame.set(0);
  player$.shuttleSpeed.set(0);
  isSeeking = false;
  if (seekTimeoutId) {
    clearTimeout(seekTimeoutId);
    seekTimeoutId = null;
  }
}
