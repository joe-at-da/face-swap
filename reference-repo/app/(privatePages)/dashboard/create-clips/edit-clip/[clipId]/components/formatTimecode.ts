import { EDITOR_FPS } from "@/lib/editorConstants";

/**
 * Converts a frame number to a MM:SS:FF timecode string.
 */
export function formatTimecode(frame: number): string {
  const totalSeconds = frame / EDITOR_FPS;
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  const f = frame % EDITOR_FPS;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}:${f.toString().padStart(2, "0")}`;
}
