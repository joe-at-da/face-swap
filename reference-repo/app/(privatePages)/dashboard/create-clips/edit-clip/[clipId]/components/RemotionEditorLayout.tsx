"use client";

import { useRef, useEffect, useCallback } from "react";
import { observer } from "@legendapp/state/react";
import type { PlayerRef } from "@remotion/player";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { RectangleHorizontal, RectangleVertical } from "lucide-react";
import type { ImperativePanelHandle } from "react-resizable-panels";
import { useSidebar } from "@/components/ui/sidebar";
import { RemotionPreview } from "./RemotionPreview";
import { EditorTimeline } from "./EditorTimeline";
import { EditorSidePanel } from "./EditorSidePanel";
import { useVideoEditorLayout } from "../hooks/useVideoEditorLayout";
import type { RemotionEditorProps } from "@/types/remotionEditor";
import {
  editor$,
  initializeEditor,
  addVideoItem,
  loadFromLocalStorage,
  flushSave,
  resetEditor,
  toggleCanvasMode,
  parseTimestampToMs,
} from "@/stores/editorStore";
import { resetPlayerStore } from "@/stores/remotionPlayerStore";
import { resetSubtitleStore } from "@/stores/subtitleStore";
import {
  setSessionDuration,
  loadSessionDuration,
} from "@/stores/sessionStore";

/** Canvas mode toggle button (16:9 / 9:16) */
const CanvasToggle = observer(function CanvasToggleInner() {
  const canvasMode = editor$.canvasMode.get();
  const handleToggle = useCallback(() => toggleCanvasMode(), []);

  return (
    <Button
      variant="outline"
      size="sm"
      className="h-7 text-[10px] gap-1 px-2"
      onClick={handleToggle}
    >
      {canvasMode === "landscape" ? (
        <RectangleHorizontal className="h-3.5 w-3.5" />
      ) : (
        <RectangleVertical className="h-3.5 w-3.5" />
      )}
      {canvasMode === "landscape" ? "16:9" : "9:16"}
    </Button>
  );
});

/**
 * Remotion Editor Layout — main editor shell.
 *
 * Three-panel layout: Preview + Timeline (left), Side Panel (right).
 * Mobile: stacked vertically.
 */
export function RemotionEditorLayout({
  mpName,
  sessionDate,
  eventTitle,
  sessionClips,
  mainMpId,
  activeClipId,
  fullVideoUrl,
  sessionLengthSeconds,
  mainClip,
  teamId,
  userId,
}: RemotionEditorProps) {
  const {
    layout,
    shouldUseSheet,
    updatePanelSizes,
    updateVideoTimelineSizes,
    setSidePanelCollapsed,
  } = useVideoEditorLayout();

  const playerRef = useRef<PlayerRef>(null);
  const sidePanelRef = useRef<ImperativePanelHandle>(null);

  // Auto-collapse app sidebar for maximum editing space
  const { open: sidebarOpen, setOpen: setSidebarOpen } = useSidebar();
  const previousSidebarState = useRef<boolean | null>(null);

  useEffect(() => {
    if (sidebarOpen) {
      previousSidebarState.current = true;
      setSidebarOpen(false);
    } else {
      previousSidebarState.current = false;
    }
    return () => {
      if (previousSidebarState.current !== null) {
        setSidebarOpen(previousSidebarState.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Initialize editor store with metadata
  useEffect(() => {
    initializeEditor(activeClipId, userId, teamId ?? null);
  }, [activeClipId, userId, teamId]);

  // Set session duration from database
  useEffect(() => {
    if (sessionLengthSeconds != null) {
      setSessionDuration(sessionLengthSeconds, fullVideoUrl);
    } else if (fullVideoUrl) {
      loadSessionDuration(fullVideoUrl).catch(() => {
        // Fallback handled inside loadSessionDuration
      });
    }
  }, [sessionLengthSeconds, fullVideoUrl]);

  // Keep a ref to sessionLengthSeconds so the load effect doesn't re-run when it resolves
  const sessionLengthRef = useRef(sessionLengthSeconds);
  sessionLengthRef.current = sessionLengthSeconds;

  // Load draft from localStorage or auto-import main clip
  useEffect(() => {
    resetEditor();
    resetPlayerStore();
    resetSubtitleStore();

    const loaded = loadFromLocalStorage(activeClipId);

    if (!loaded && mainClip && fullVideoUrl) {
      const startMs = parseTimestampToMs(mainClip.start_timestamp);
      const endMs = parseTimestampToMs(mainClip.end_timestamp);
      const durationSeconds = (endMs - startMs) / 1000;

      addVideoItem({
        src: fullVideoUrl,
        clipId: mainClip.id,
        startTimestamp: mainClip.start_timestamp,
        endTimestamp: mainClip.end_timestamp,
        sessionDurationMs: (sessionLengthRef.current ?? 0) * 1000,
        mpName: mainClip.parliament_members.display_name ?? "Unknown MP",
        transcript: mainClip.transcript ?? "",
        thumbnailUrl: mainClip.thumbnail_url,
        durationSeconds,
      });
    }
  }, [activeClipId, mainClip, fullVideoUrl]);

  // beforeunload: flush pending saves
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      flushSave();
      if (editor$.isDirty.peek()) {
        e.preventDefault();
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      flushSave(); // Flush pending saves on SPA navigation (unmount without beforeunload)
    };
  }, []);

  if (shouldUseSheet) {
    // Mobile/Tablet: Stacked vertically
    return (
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-border px-4 py-2">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">{mpName}</h2>
              <p className="text-xs text-muted-foreground">{sessionDate}</p>
            </div>
            <CanvasToggle />
          </div>
        </div>

        {/* Preview */}
        <div className="flex-[2] min-h-0">
          <RemotionPreview playerRef={playerRef} />
        </div>

        {/* Timeline */}
        <div className="flex-1 min-h-[150px] border-t border-border">
          <EditorTimeline playerRef={playerRef} />
        </div>
      </div>
    );
  }

  // Desktop: Horizontal ResizablePanelGroup
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <ResizablePanelGroup
        direction="horizontal"
        className="h-full"
        onLayout={(sizes) => updatePanelSizes(sizes)}
      >
        {/* Left Panel: Header + Preview + Timeline */}
        <ResizablePanel defaultSize={70} minSize={50} collapsible={false}>
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex-shrink-0 border-b border-border px-4 py-2">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold">{mpName}</h2>
                  <p className="text-xs text-muted-foreground">
                    {sessionDate}
                    {eventTitle ? ` — ${eventTitle}` : ""}
                  </p>
                </div>
                <CanvasToggle />
              </div>
            </div>

            {/* Preview + Timeline */}
            <div className="flex-1 overflow-hidden min-h-0">
              <ResizablePanelGroup
                direction="vertical"
                className="h-full"
                onLayout={(sizes) => updateVideoTimelineSizes(sizes)}
              >
                {/* Preview */}
                <ResizablePanel
                  defaultSize={layout.videoSize}
                  minSize={30}
                  collapsible={false}
                >
                  <RemotionPreview playerRef={playerRef} />
                </ResizablePanel>

                <ResizableHandle />

                {/* Timeline */}
                <ResizablePanel
                  defaultSize={layout.timelineSize}
                  minSize={15}
                  collapsible={false}
                  className="overflow-hidden"
                >
                  <div className="h-full border-t border-border">
                    <EditorTimeline playerRef={playerRef} />
                  </div>
                </ResizablePanel>
              </ResizablePanelGroup>
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle />

        {/* Right Panel: Side Panel */}
        <ResizablePanel
          ref={sidePanelRef}
          defaultSize={30}
          minSize={20}
          maxSize={40}
          collapsible
          onCollapse={() => setSidePanelCollapsed(true)}
          onExpand={() => setSidePanelCollapsed(false)}
          className="overflow-hidden"
        >
          <div className="h-full border-l border-border">
            <EditorSidePanel
              sessionClips={sessionClips}
              fullVideoUrl={fullVideoUrl}
              mainMpId={mainMpId}
              playerRef={playerRef}
              sessionLengthSeconds={sessionLengthSeconds}
            />
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}

