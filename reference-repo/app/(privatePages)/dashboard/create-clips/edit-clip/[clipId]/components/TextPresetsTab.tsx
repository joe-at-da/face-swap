"use client";

import { useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { addTextItem, selectItem } from "@/stores/editorStore";
import { player$ } from "@/stores/remotionPlayerStore";
import type { TextAnimation } from "@/types/remotionEditor";
import { EDITOR_FPS } from "@/lib/editorConstants";

interface TextPreset {
  name: string;
  description: string;
  text: string;
  fontSize: number;
  color: string;
  backgroundColor: string;
  animation: TextAnimation;
  position: { x: number; y: number };
  durationInFrames: number;
  // Preview layout hints
  previewAlign: "flex-start" | "center" | "flex-end";
  previewJustify: "flex-start" | "center" | "flex-end";
}

const TEXT_PRESETS: TextPreset[] = [
  {
    name: "Title",
    description: "Large centered title",
    text: "Title Text",
    fontSize: 72,
    color: "#ffffff",
    backgroundColor: "transparent",
    animation: "fade-in",
    position: { x: 0.5, y: 0.5 },
    durationInFrames: EDITOR_FPS *3,
    previewAlign: "center",
    previewJustify: "center",
  },
  {
    name: "Lower Third",
    description: "Name/title bar at bottom",
    text: "Speaker Name",
    fontSize: 36,
    color: "#ffffff",
    backgroundColor: "rgba(0,0,0,0.7)",
    animation: "slide-in-left",
    position: { x: 0.1, y: 0.85 },
    durationInFrames: EDITOR_FPS *4,
    previewAlign: "flex-end",
    previewJustify: "flex-start",
  },
  {
    name: "Caption",
    description: "Small text at bottom center",
    text: "Caption text here",
    fontSize: 24,
    color: "#ffffff",
    backgroundColor: "rgba(0,0,0,0.5)",
    animation: "fade-in",
    position: { x: 0.5, y: 0.9 },
    durationInFrames: EDITOR_FPS *3,
    previewAlign: "flex-end",
    previewJustify: "center",
  },
  {
    name: "Heading",
    description: "Bold heading at top",
    text: "Heading",
    fontSize: 56,
    color: "#ffffff",
    backgroundColor: "transparent",
    animation: "slide-in-right",
    position: { x: 0.5, y: 0.15 },
    durationInFrames: EDITOR_FPS *3,
    previewAlign: "flex-start",
    previewJustify: "center",
  },
  {
    name: "Quote",
    description: "Stylized quote text",
    text: '\u201CQuote text here\u201D',
    fontSize: 40,
    color: "#e0e0e0",
    backgroundColor: "transparent",
    animation: "typewriter",
    position: { x: 0.5, y: 0.5 },
    durationInFrames: EDITOR_FPS *5,
    previewAlign: "center",
    previewJustify: "center",
  },
];

const ANIMATION_LABELS: Record<TextAnimation, string> = {
  "none": "Static",
  "fade-in": "Fade",
  "slide-in-left": "Slide L",
  "slide-in-right": "Slide R",
  "typewriter": "Type",
};

export function TextPresetsTab() {
  const handleInsertPreset = useCallback(
    (preset: TextPreset) => {
      const currentFrame = player$.currentFrame.peek();

      const newItem = addTextItem({
        text: preset.text,
        fontSize: preset.fontSize,
        color: preset.color,
        backgroundColor: preset.backgroundColor,
        animation: preset.animation,
        position: preset.position,
        insertAtFrame: currentFrame,
        durationInFrames: preset.durationInFrames,
      });

      selectItem(newItem.id);
    },
    []
  );

  return (
    <ScrollArea className="h-full">
      <div className="p-3">
        <p className="text-xs text-muted-foreground mb-3">
          Click a preset to insert at the playhead position.
        </p>

        <div className="grid grid-cols-2 gap-2">
          {TEXT_PRESETS.map((preset) => {
            const bgIsTransparent = preset.backgroundColor === "transparent";

            return (
              <button
                key={preset.name}
                onClick={() => handleInsertPreset(preset)}
                className="w-full text-left rounded-lg border border-border overflow-hidden hover:border-primary/50 hover:ring-1 hover:ring-primary/20 transition-all group"
              >
                {/* Dark 16:9 preview with positioned text */}
                <div
                  className="relative aspect-video w-full flex overflow-hidden px-2 py-1.5"
                  style={{
                    background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
                    alignItems: preset.previewAlign,
                    justifyContent: preset.previewJustify,
                  }}
                >
                  <span
                    className="truncate max-w-full"
                    style={{
                      color: preset.color,
                      fontSize: `${Math.min(preset.fontSize / 5, 14)}px`,
                      fontWeight: preset.fontSize >= 48 ? 700 : 400,
                      backgroundColor: bgIsTransparent
                        ? "transparent"
                        : preset.backgroundColor,
                      padding: bgIsTransparent ? 0 : "1px 5px",
                      borderRadius: bgIsTransparent ? 0 : 2,
                      fontStyle: preset.name === "Quote" ? "italic" : "normal",
                    }}
                  >
                    {preset.text}
                  </span>
                  {/* Animation badge */}
                  <span className="absolute top-1 right-1 text-[9px] text-white/40 bg-white/10 rounded px-1 py-0.5 leading-none">
                    {ANIMATION_LABELS[preset.animation]}
                  </span>
                </div>
                {/* Label */}
                <div className="px-2 py-1.5 bg-card">
                  <p className="text-xs font-medium leading-tight">
                    {preset.name}
                  </p>
                  <p className="text-[10px] text-muted-foreground leading-tight">
                    {preset.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </ScrollArea>
  );
}
