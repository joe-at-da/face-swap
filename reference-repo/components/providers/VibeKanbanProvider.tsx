"use client";

import dynamic from "next/dynamic";

const VibeKanbanWebCompanion = dynamic(
  () =>
    import("vibe-kanban-web-companion").then(
      (mod) => mod.VibeKanbanWebCompanion
    ),
  { ssr: false }
);

/**
 * Vibe Kanban Web Companion Provider
 * Renders the Vibe Kanban companion component in development mode only
 * Uses dynamic import with ssr: false to prevent hydration mismatches
 */
export function VibeKanbanProvider() {
  // Only render in development mode
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  return <VibeKanbanWebCompanion />;
}
