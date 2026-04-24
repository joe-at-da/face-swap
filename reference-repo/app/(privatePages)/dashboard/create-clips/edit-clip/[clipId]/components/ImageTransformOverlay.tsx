"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { updateItemProperties } from "@/stores/editorStore";
import type { TimelineItem } from "@/types/remotionEditor";
import { type Corner, cornerHandleStyle } from "./cornerHandleUtils";

interface ImageTransformOverlayProps {
  item: TimelineItem;
  onDeselect: () => void;
}

const HANDLE_SIZE = 8;

interface DragState {
  type: "move" | "resize";
  startMouseX: number;
  startMouseY: number;
  startPosX: number;
  startPosY: number;
  startWidthPercent: number;
  parentRect: DOMRect;
  startDistFromCenter: number;
  currentPosX: number;
  currentPosY: number;
  currentWidthPercent: number;
}

export function ImageTransformOverlay({
  item,
  onDeselect,
}: ImageTransformOverlayProps) {
  const posX = item.position?.x ?? 0.5;
  const posY = item.position?.y ?? 0.5;
  const widthPct = item.imageWidthPercent ?? 30;

  const [localPosX, setLocalPosX] = useState(posX);
  const [localPosY, setLocalPosY] = useState(posY);
  const [localWidthPct, setLocalWidthPct] = useState(widthPct);

  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);

  // Sync from external changes (sliders, undo/redo) when not dragging
  useEffect(() => {
    if (dragRef.current) return;
    setLocalPosX(posX);
    setLocalPosY(posY);
    setLocalWidthPct(widthPct);
  }, [posX, posY, widthPct]);

  // Escape to deselect
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onDeselect();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onDeselect]);

  // Window-level pointer listeners for drag
  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;

      if (drag.type === "move") {
        const deltaX = e.clientX - drag.startMouseX;
        const deltaY = e.clientY - drag.startMouseY;
        // Convert pixel delta to normalized 0-1 coordinates
        const normDeltaX = deltaX / drag.parentRect.width;
        const normDeltaY = deltaY / drag.parentRect.height;
        const newX = Math.max(0, Math.min(1, drag.startPosX + normDeltaX));
        const newY = Math.max(0, Math.min(1, drag.startPosY + normDeltaY));
        drag.currentPosX = newX;
        drag.currentPosY = newY;
        setLocalPosX(newX);
        setLocalPosY(newY);
      } else {
        // Resize: scale width based on distance from center ratio
        const centerX =
          drag.parentRect.left + drag.startPosX * drag.parentRect.width;
        const centerY =
          drag.parentRect.top + drag.startPosY * drag.parentRect.height;
        const currentDist = Math.hypot(
          e.clientX - centerX,
          e.clientY - centerY
        );
        const ratio =
          drag.startDistFromCenter > 0
            ? currentDist / drag.startDistFromCenter
            : 1;
        const newWidth = Math.max(5, Math.min(100, drag.startWidthPercent * ratio));
        drag.currentWidthPercent = newWidth;
        setLocalWidthPct(newWidth);
      }
    };

    const handlePointerUp = () => {
      const drag = dragRef.current;
      if (!drag) return;

      if (drag.type === "move") {
        updateItemProperties(item.id, {
          position: { x: drag.currentPosX, y: drag.currentPosY },
        });
      } else {
        updateItemProperties(item.id, {
          imageWidthPercent: Math.round(drag.currentWidthPercent),
        });
      }

      dragRef.current = null;
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [item.id]);

  // Move: pointerdown on the bounding box body
  const handleBodyPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if ((e.target as HTMLElement).dataset.corner) return;
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      dragRef.current = {
        type: "move",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPosX: localPosX,
        startPosY: localPosY,
        startWidthPercent: localWidthPct,
        parentRect: parent.getBoundingClientRect(),
        startDistFromCenter: 0,
        currentPosX: localPosX,
        currentPosY: localPosY,
        currentWidthPercent: localWidthPct,
      };
      e.stopPropagation();
    },
    [localPosX, localPosY, localWidthPct]
  );

  // Resize: pointerdown on a corner handle
  const handleCornerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.stopPropagation();
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      const parentRect = parent.getBoundingClientRect();
      const centerX = parentRect.left + localPosX * parentRect.width;
      const centerY = parentRect.top + localPosY * parentRect.height;
      const dist = Math.hypot(e.clientX - centerX, e.clientY - centerY);

      dragRef.current = {
        type: "resize",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPosX: localPosX,
        startPosY: localPosY,
        startWidthPercent: localWidthPct,
        parentRect,
        startDistFromCenter: dist,
        currentPosX: localPosX,
        currentPosY: localPosY,
        currentWidthPercent: localWidthPct,
      };
    },
    [localPosX, localPosY, localWidthPct]
  );

  // Bounding box: center at (posX, posY), width = widthPct% of parent
  // Height approximated as 75% of width (3:4 aspect ratio estimate)
  const boxWidthPct = localWidthPct;
  const boxHeightPct = localWidthPct * 0.75;
  const left = localPosX * 100 - boxWidthPct / 2;
  const top = localPosY * 100 - boxHeightPct / 2;

  return (
    <div
      ref={containerRef}
      data-image-overlay
      onPointerDown={handleBodyPointerDown}
      style={{
        position: "absolute",
        left: `${left}%`,
        top: `${top}%`,
        width: `${boxWidthPct}%`,
        height: `${boxHeightPct}%`,
        border: "2px dashed hsl(var(--primary))",
        boxShadow: "0 0 0 9999px rgba(0,0,0,0.15)",
        cursor: "move",
        zIndex: 20,
        boxSizing: "border-box",
        pointerEvents: "auto",
        userSelect: "none",
        touchAction: "none",
      }}
    >
      {(
        ["top-left", "top-right", "bottom-left", "bottom-right"] as Corner[]
      ).map((corner) => (
        <div
          key={corner}
          data-corner={corner}
          style={cornerHandleStyle(corner, HANDLE_SIZE)}
          onPointerDown={handleCornerPointerDown}
        />
      ))}
    </div>
  );
}
