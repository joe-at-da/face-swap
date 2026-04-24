"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { updateItemProperties } from "@/stores/editorStore";
import type { TimelineItem } from "@/types/remotionEditor";
import { cornerHandleStyle } from "./cornerHandleUtils";

interface InlineTextEditorProps {
  item: TimelineItem;
  scale: number;
  onCommit: (newText: string) => void;
  onCancel: () => void;
}

const HANDLE_SIZE = 6;

interface DragState {
  type: "move" | "resize";
  startMouseX: number;
  startMouseY: number;
  startPosX: number;
  startPosY: number;
  startFontSize: number;
  parentRect: DOMRect;
  // Updated continuously during drag so pointerup can read final values
  currentPosX: number;
  currentPosY: number;
  currentFontSize: number;
}

export function InlineTextEditor({
  item,
  scale,
  onCommit,
  onCancel,
}: InlineTextEditorProps) {
  const [text, setText] = useState(item.text ?? "");
  const [localPos, setLocalPos] = useState({
    x: item.position?.x ?? 0.5,
    y: item.position?.y ?? 0.5,
  });
  const [localFontSize, setLocalFontSize] = useState(item.fontSize ?? 48);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const originalText = useRef(item.text ?? "");
  const dragRef = useRef<DragState | null>(null);

  // Auto-focus on mount (cursor at end)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  }, []);

  // Window-level pointer listeners for drag/resize
  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;

      if (drag.type === "move") {
        const deltaX = e.clientX - drag.startMouseX;
        const deltaY = e.clientY - drag.startMouseY;
        const newX = Math.max(0, Math.min(1, drag.startPosX + deltaX / drag.parentRect.width));
        const newY = Math.max(0, Math.min(1, drag.startPosY + deltaY / drag.parentRect.height));
        drag.currentPosX = newX;
        drag.currentPosY = newY;
        setLocalPos({ x: newX, y: newY });
      } else {
        const deltaY = drag.startMouseY - e.clientY; // up = bigger
        const newSize = Math.max(12, Math.min(200, Math.round(drag.startFontSize + deltaY / scale)));
        drag.currentFontSize = newSize;
        setLocalFontSize(newSize);
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
        updateItemProperties(item.id, { fontSize: drag.currentFontSize });
      }

      dragRef.current = null;
      textareaRef.current?.focus();
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [item.id, scale]);

  // --- Move: pointerdown on container (not textarea, not corner handles) ---
  const handleContainerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      dragRef.current = {
        type: "move",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPosX: localPos.x,
        startPosY: localPos.y,
        startFontSize: localFontSize,
        parentRect: parent.getBoundingClientRect(),
        currentPosX: localPos.x,
        currentPosY: localPos.y,
        currentFontSize: localFontSize,
      };
      e.preventDefault(); // Prevent text selection during drag
    },
    [localPos, localFontSize]
  );

  // --- Resize: pointerdown on a corner handle ---
  const handleCornerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.stopPropagation(); // Don't trigger container move
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      dragRef.current = {
        type: "resize",
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPosX: localPos.x,
        startPosY: localPos.y,
        startFontSize: localFontSize,
        parentRect: parent.getBoundingClientRect(),
        currentPosX: localPos.x,
        currentPosY: localPos.y,
        currentFontSize: localFontSize,
      };
      e.preventDefault();
    },
    [localPos, localFontSize]
  );

  // --- Text editing handlers ---
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      e.stopPropagation(); // Prevent editor shortcuts (Space=play, etc.)
      if (e.key === "Escape") {
        onCancel();
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onCommit(text);
      }
    },
    [text, onCommit, onCancel]
  );

  const handleBlur = useCallback(() => {
    // Skip blur during drag (textarea loses focus when clicking container/handles)
    if (dragRef.current) return;
    if (text !== originalText.current) {
      onCommit(text);
    } else {
      onCancel();
    }
  }, [text, onCommit, onCancel]);

  return (
    <div
      ref={containerRef}
      data-inline-editor="true"
      onPointerDown={handleContainerPointerDown}
      style={{
        position: "absolute",
        left: `${localPos.x * 100}%`,
        top: `${localPos.y * 100}%`,
        transform: "translate(-50%, -50%)",
        zIndex: 20,
        maxWidth: "80%",
        width: "fit-content",
        cursor: "move",
        border: "2px dashed hsl(var(--primary))",
        boxShadow: "0 0 0 1px rgba(0,0,0,0.3)",
        borderRadius: 4 * scale,
        padding: 4,
        boxSizing: "border-box" as const,
      }}
    >
      {/* Corner handles */}
      <div data-corner="true" style={cornerHandleStyle("top-left", HANDLE_SIZE)} onPointerDown={handleCornerPointerDown} />
      <div data-corner="true" style={cornerHandleStyle("top-right", HANDLE_SIZE)} onPointerDown={handleCornerPointerDown} />
      <div data-corner="true" style={cornerHandleStyle("bottom-left", HANDLE_SIZE)} onPointerDown={handleCornerPointerDown} />
      <div data-corner="true" style={cornerHandleStyle("bottom-right", HANDLE_SIZE)} onPointerDown={handleCornerPointerDown} />

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          fontSize: `${localFontSize * scale}px`,
          fontFamily: item.fontFamily ?? "Inter, sans-serif",
          fontWeight: 700,
          color: item.color ?? "#ffffff",
          backgroundColor: item.backgroundColor ?? "transparent",
          padding: `${8 * scale}px ${16 * scale}px`,
          textAlign: "center" as const,
          minWidth: `${120 * scale}px`,
          whiteSpace: "pre-wrap",
          outline: "none",
          border: "none",
          resize: "none",
          caretColor: "hsl(var(--primary))",
          margin: 0,
          overflow: "hidden",
          boxSizing: "border-box" as const,
          cursor: "text",
          fieldSizing: "content",
        } as React.CSSProperties}
      />
    </div>
  );
}
