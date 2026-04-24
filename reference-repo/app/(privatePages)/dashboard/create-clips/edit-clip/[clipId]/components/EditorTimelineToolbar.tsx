"use client";

import { useCallback } from "react";
import { observer } from "@legendapp/state/react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ZoomIn,
  ZoomOut,
  Magnet,
  Scissors,
  Undo2,
  Redo2,
  Maximize2,
  Plus,
} from "lucide-react";
import { editor$, toggleSnap, setZoomLevel, undo, redo, addTrack } from "@/stores/editorStore";
import { player$ } from "@/stores/remotionPlayerStore";
import { formatTimecode } from "./formatTimecode";

interface EditorTimelineToolbarProps {
  onSplitAtPlayhead: () => void;
  onFitToView: () => void;
}

function EditorTimelineToolbarInner({
  onSplitAtPlayhead,
  onFitToView,
}: EditorTimelineToolbarProps) {
  const snapEnabled = editor$.snapEnabled.get();
  const zoomLevel = editor$.zoomLevel.get();
  const currentFrame = player$.currentFrame.get();
  const hasUndo = editor$.undoStack.get().length > 0;
  const hasRedo = editor$.redoStack.get().length > 0;

  const handleZoomChange = useCallback((value: number[]) => {
    setZoomLevel(value[0]);
  }, []);

  return (
    <div className="flex items-center gap-1 px-2 py-1 border-t border-border bg-card">
      {/* Undo/Redo */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={undo}
            disabled={!hasUndo}
          >
            <Undo2 className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Undo (Ctrl+Z)</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={redo}
            disabled={!hasRedo}
          >
            <Redo2 className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Redo (Ctrl+Shift+Z)</TooltipContent>
      </Tooltip>

      <div className="w-px h-4 bg-border mx-1" />

      {/* Split (razor) */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onSplitAtPlayhead}
          >
            <Scissors className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Split at playhead (C)</TooltipContent>
      </Tooltip>

      {/* Snap toggle */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={snapEnabled ? "secondary" : "ghost"}
            size="icon"
            className={`h-7 w-7 ${snapEnabled ? "ring-1 ring-primary/30" : ""}`}
            onClick={toggleSnap}
          >
            <Magnet className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          Snap {snapEnabled ? "(on)" : "(off)"} (S)
        </TooltipContent>
      </Tooltip>

      <div className="w-px h-4 bg-border mx-1" />

      {/* Zoom controls */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setZoomLevel(zoomLevel - 20)}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Zoom out (-)</TooltipContent>
      </Tooltip>

      <Slider
        value={[zoomLevel]}
        min={10}
        max={500}
        step={10}
        onValueChange={handleZoomChange}
        className="w-28"
      />

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setZoomLevel(zoomLevel + 20)}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Zoom in (=)</TooltipContent>
      </Tooltip>

      {/* Fit to view */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onFitToView}
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Fit to view</TooltipContent>
      </Tooltip>

      <div className="w-px h-4 bg-border mx-1" />

      {/* Add track */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs gap-1"
            onClick={() => addTrack()}
          >
            <Plus className="h-3.5 w-3.5" />
            Track
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Add track</TooltipContent>
      </Tooltip>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Current time display */}
      <span className="font-mono text-xs text-muted-foreground tabular-nums">
        {formatTimecode(currentFrame)}
      </span>
    </div>
  );
}

export const EditorTimelineToolbar = observer(EditorTimelineToolbarInner);
