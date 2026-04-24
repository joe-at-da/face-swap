"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { updateItemProperties, peekItem } from "@/stores/editorStore";
import type { TimelineItem } from "@/types/remotionEditor";
import { type Corner, cornerHandleStyle } from "./cornerHandleUtils";

interface VideoTransformOverlayProps {
  item: TimelineItem;
  onDeselect: () => void;
}

const HANDLE_SIZE = 8;

interface DragState {
  type: "move" | "resize";
  startMouseX: number;
  startMouseY: number;
  startTranslateX: number;
  startTranslateY: number;
  startScale: number;
  parentRect: DOMRect;
  /** Distance from center at drag start (for resize) */
  startDistFromCenter: number;
  // Updated continuously during drag
  currentTranslateX: number;
  currentTranslateY: number;
  currentScale: number;
}

export function VideoTransformOverlay({
  item,
  onDeselect,
}: VideoTransformOverlayProps) {
  const transform = item.transform ?? {};
  const [localTranslateX, setLocalTranslateX] = useState(
    transform.translateX ?? 0
  );
  const [localTranslateY, setLocalTranslateY] = useState(
    transform.translateY ?? 0
  );
  const [localScale, setLocalScale] = useState(transform.scale ?? 1);

  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);

  // Sync from external changes (sliders, undo/redo) when not dragging
  useEffect(() => {
    if (dragRef.current) return;
    setLocalTranslateX(transform.translateX ?? 0);
    setLocalTranslateY(transform.translateY ?? 0);
    setLocalScale(transform.scale ?? 1);
  }, [transform.translateX, transform.translateY, transform.scale]);

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
        // Convert pixel delta to percentage of container
        const pctDeltaX = (deltaX / drag.parentRect.width) * 100;
        const pctDeltaY = (deltaY / drag.parentRect.height) * 100;
        const newTX = Math.max(
          -100,
          Math.min(100, drag.startTranslateX + pctDeltaX)
        );
        const newTY = Math.max(
          -100,
          Math.min(100, drag.startTranslateY + pctDeltaY)
        );
        drag.currentTranslateX = newTX;
        drag.currentTranslateY = newTY;
        setLocalTranslateX(newTX);
        setLocalTranslateY(newTY);
      } else {
        // Resize: scale based on distance from center ratio
        const centerX = drag.parentRect.left + drag.parentRect.width / 2;
        const centerY = drag.parentRect.top + drag.parentRect.height / 2;
        const currentDist = Math.hypot(
          e.clientX - centerX,
          e.clientY - centerY
        );
        const ratio =
          drag.startDistFromCenter > 0
            ? currentDist / drag.startDistFromCenter
            : 1;
        const newScale = Math.max(
          0.1,
          Math.min(4.0, drag.startScale * ratio)
        );
        drag.currentScale = newScale;
        setLocalScale(newScale);
      }
    };

    const handlePointerUp = () => {
      const drag = dragRef.current;
      if (!drag) return;

      // Read current transform from the store to avoid stale closure
      const currentTransform = peekItem(item.id)?.transform;

      const updates =
        drag.type === "move"
          ? {
              transform: {
                ...currentTransform,
                translateX: drag.currentTranslateX,
                translateY: drag.currentTranslateY,
              },
            }
          : {
              transform: {
                ...currentTransform,
                scale: drag.currentScale,
              },
            };

      updateItemProperties(item.id, updates);
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
      // Don't trigger on corner handles
      if ((e.target as HTMLElement).dataset.corner) return;
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      dragRef.current = {
        type: "move",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startTranslateX: localTranslateX,
        startTranslateY: localTranslateY,
        startScale: localScale,
        parentRect: parent.getBoundingClientRect(),
        startDistFromCenter: 0,
        currentTranslateX: localTranslateX,
        currentTranslateY: localTranslateY,
        currentScale: localScale,
      };
      e.stopPropagation();
    },
    [localTranslateX, localTranslateY, localScale]
  );

  // Resize: pointerdown on a corner handle
  const handleCornerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.stopPropagation();
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      const parentRect = parent.getBoundingClientRect();
      const centerX = parentRect.left + parentRect.width / 2;
      const centerY = parentRect.top + parentRect.height / 2;
      const dist = Math.hypot(e.clientX - centerX, e.clientY - centerY);

      dragRef.current = {
        type: "resize",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startTranslateX: localTranslateX,
        startTranslateY: localTranslateY,
        startScale: localScale,
        parentRect,
        startDistFromCenter: dist,
        currentTranslateX: localTranslateX,
        currentTranslateY: localTranslateY,
        currentScale: localScale,
      };
    },
    [localTranslateX, localTranslateY, localScale]
  );

  // Bounding box position: matching ClipSequence transform math
  // translate(TX%, TY%) scale(S) with transformOrigin: center center
  const left = 50 + localTranslateX - localScale * 50;
  const top = 50 + localTranslateY - localScale * 50;
  const width = localScale * 100;
  const height = localScale * 100;

  return (
    <div
      ref={containerRef}
      data-video-overlay
      onPointerDown={handleBodyPointerDown}
      style={{
        position: "absolute",
        left: `${left}%`,
        top: `${top}%`,
        width: `${width}%`,
        height: `${height}%`,
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
      {/* Corner handles */}
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
