"use client";

import { useEffect, useCallback, useRef } from "react";
import type { PlayerRef } from "@remotion/player";
import {
  editor$,
  removeItem,
  undo,
  redo,
  resolveTargetItem,
  findAllItemsAtFrame,
  splitItem,
  selectItem,
  setZoomLevel,
  toggleSnap,
} from "@/stores/editorStore";
import {
  player$,
  shuttleForward,
  shuttleBackward,
  shuttleStop,
  beginSeek,
} from "@/stores/remotionPlayerStore";

interface UseEditorKeyboardOptions {
  playerRef: React.RefObject<PlayerRef | null>;
}

export function useEditorKeyboard({ playerRef }: UseEditorKeyboardOptions) {
  // Prevent handling keyboard events when typing in inputs
  const isInputFocused = useRef(false);

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

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ignore if focused on text input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        isInputFocused.current = true;
        return;
      }
      isInputFocused.current = false;

      const player = playerRef.current;

      // Ctrl/Cmd shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "z":
            e.preventDefault();
            if (e.shiftKey) {
              redo();
            } else {
              undo();
            }
            return;
          case "d":
            e.preventDefault();
            // Ctrl+D: apply default transition (Phase 3)
            return;
        }
      }

      switch (e.key) {
        case " ": // Space: play/pause
          e.preventDefault();
          if (!player) return;
          if (player$.isPlaying.peek()) {
            player.pause();
          } else {
            player.play();
          }
          break;

        case "j": // J: shuttle backward
        case "J":
          e.preventDefault();
          shuttleBackward();
          break;

        case "k": // K: shuttle stop / pause
        case "K":
          e.preventDefault();
          shuttleStop();
          if (player) player.pause();
          break;

        case "l": // L: shuttle forward
        case "L":
          e.preventDefault();
          shuttleForward();
          break;

        case "c": // C: cut/split at playhead
        case "C":
          e.preventDefault();
          handleSplitAtPlayhead();
          break;

        case "d": // D: delete selected item
        case "D":
        case "Delete":
        case "Backspace": {
          e.preventDefault();
          const selectedId = editor$.selectedItemId.peek();
          if (selectedId) {
            removeItem(selectedId);
          }
          break;
        }

        case "Escape":
          selectItem(null);
          break;

        case "s":
        case "S":
          e.preventDefault();
          toggleSnap();
          break;

        case "ArrowLeft":
          e.preventDefault();
          if (player) {
            beginSeek();
            const delta = e.shiftKey ? 10 : 1;
            const frame = Math.max(0, player$.currentFrame.peek() - delta);
            player.seekTo(frame);
            player$.currentFrame.set(frame);
          }
          break;

        case "ArrowRight":
          e.preventDefault();
          if (player) {
            const total = editor$.totalDurationInFrames.peek();
            if (total <= 0) break;
            beginSeek();
            const delta = e.shiftKey ? 10 : 1;
            const frame = Math.min(
              total - 1,
              player$.currentFrame.peek() + delta
            );
            player.seekTo(frame);
            player$.currentFrame.set(frame);
          }
          break;

        case "Home":
          e.preventDefault();
          if (player) {
            beginSeek();
            player.seekTo(0);
            player$.currentFrame.set(0);
          }
          break;

        case "End":
          e.preventDefault();
          if (player) {
            beginSeek();
            const endFrame = Math.max(0, editor$.totalDurationInFrames.peek() - 1);
            player.seekTo(endFrame);
            player$.currentFrame.set(endFrame);
          }
          break;

        case "=":
        case "+":
          e.preventDefault();
          setZoomLevel(editor$.zoomLevel.peek() + 20);
          break;

        case "-":
          e.preventDefault();
          setZoomLevel(editor$.zoomLevel.peek() - 20);
          break;
      }
    },
    [playerRef, handleSplitAtPlayhead]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return { handleSplitAtPlayhead };
}
