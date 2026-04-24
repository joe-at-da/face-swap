"use client";

import { useCallback } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateItemProperties, peekItem } from "@/stores/editorStore";
import type { TimelineItem, ItemTransform, FitMode, TextAnimation } from "@/types/remotionEditor";
import Image from "next/image";
import { PropertySlider } from "./PropertySlider";
import { EDITOR_FPS } from "@/lib/editorConstants";

// ─── ImagePropertiesPanel ───────────────────────────────────────────────────

interface ImagePropertiesPanelProps {
  item: TimelineItem;
}

export function ImagePropertiesPanel({ item }: ImagePropertiesPanelProps) {
  const durationSec = (item.durationInFrames / EDITOR_FPS).toFixed(1);
  const t = item.transform ?? {};

  const handleTransformCommit = useCallback(
    (key: keyof ItemTransform, value: number) => {
      const current = peekItem(item.id)?.transform ?? {};
      updateItemProperties(item.id, {
        transform: { ...current, [key]: value },
      });
    },
    [item.id]
  );

  const handleResetTransform = useCallback(() => {
    updateItemProperties(item.id, {
      transform: undefined,
      flipH: undefined,
      flipV: undefined,
      position: { x: 0.5, y: 0.5 },
      imageWidthPercent: 30,
      opacity: 1,
    });
  }, [item.id]);

  const handleFlipH = useCallback(
    (checked: boolean) => updateItemProperties(item.id, { flipH: checked }),
    [item.id]
  );

  const handleFlipV = useCallback(
    (checked: boolean) => updateItemProperties(item.id, { flipV: checked }),
    [item.id]
  );

  return (
    <div className="p-3 space-y-4">
      {/* Preview thumbnail */}
      {item.src && (
        <div className="flex items-center gap-3">
          <div className="relative h-12 w-12 rounded border border-border overflow-hidden bg-muted flex-shrink-0">
            <Image
              src={item.src}
              alt="Image preview"
              fill
              className="object-contain"
            />
          </div>
          <div>
            <p className="text-sm font-medium">Image overlay</p>
            <p className="text-[10px] text-muted-foreground">{durationSec}s</p>
          </div>
        </div>
      )}

      {/* Width */}
      <PropertySlider
        label="Width"
        value={item.imageWidthPercent ?? 30}
        min={5}
        max={100}
        step={1}
        formatLabel={(v) => `${v}%`}
        onCommit={(v) => updateItemProperties(item.id, { imageWidthPercent: v })}
      />

      {/* Position */}
      <PropertySlider
        label="Position X"
        value={Math.round((item.position?.x ?? 0.5) * 100)}
        min={0}
        max={100}
        step={1}
        formatLabel={(v) => `${v}%`}
        onCommit={(v) =>
          updateItemProperties(item.id, {
            position: { x: v / 100, y: item.position?.y ?? 0.5 },
          })
        }
      />

      <PropertySlider
        label="Position Y"
        value={Math.round((item.position?.y ?? 0.5) * 100)}
        min={0}
        max={100}
        step={1}
        formatLabel={(v) => `${v}%`}
        onCommit={(v) =>
          updateItemProperties(item.id, {
            position: { x: item.position?.x ?? 0.5, y: v / 100 },
          })
        }
      />

      {/* Opacity */}
      <PropertySlider
        label="Opacity"
        value={item.opacity ?? 1}
        min={0}
        max={1}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => updateItemProperties(item.id, { opacity: v })}
      />

      {/* Transform section */}
      <div className="pt-2 border-t border-border space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium">Transform</p>
          <button
            onClick={handleResetTransform}
            className="text-[10px] text-muted-foreground hover:text-foreground"
          >
            Reset all
          </button>
        </div>

        <PropertySlider
          label="Scale"
          value={t.scale ?? 1}
          min={0.5}
          max={4}
          step={0.1}
          formatLabel={(v) => `${Math.round(v * 100)}%`}
          onCommit={(v) => handleTransformCommit("scale", v)}
        />

        <PropertySlider
          label="Rotation"
          value={t.rotation ?? 0}
          min={-180}
          max={180}
          step={1}
          formatLabel={(v) => `${v}\u00B0`}
          onCommit={(v) => handleTransformCommit("rotation", v)}
        />

        {/* Flip toggles */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs">Flip H</Label>
            <Switch
              checked={item.flipH ?? false}
              onCheckedChange={handleFlipH}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-xs">Flip V</Label>
            <Switch
              checked={item.flipV ?? false}
              onCheckedChange={handleFlipV}
            />
          </div>
        </div>
      </div>

      {/* Object Fit */}
      <div className="space-y-1.5">
        <Label className="text-xs">Object Fit</Label>
        <Select
          value={item.fitMode ?? "contain"}
          onValueChange={(v) =>
            updateItemProperties(item.id, { fitMode: v as FitMode })
          }
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="contain">Contain</SelectItem>
            <SelectItem value="cover">Cover</SelectItem>
            <SelectItem value="fill">Fill</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Animation */}
      <div className="space-y-1.5">
        <Label className="text-xs">Animation</Label>
        <Select
          value={item.animation ?? "none"}
          onValueChange={(v) =>
            updateItemProperties(item.id, {
              animation: v as TextAnimation,
            })
          }
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            <SelectItem value="fade-in">Fade In</SelectItem>
            <SelectItem value="slide-in-left">Slide In Left</SelectItem>
            <SelectItem value="slide-in-right">Slide In Right</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Position info */}
      <div className="pt-2 border-t border-border space-y-1">
        <p className="text-[10px] text-muted-foreground font-medium">
          Timeline
        </p>
        <div className="grid grid-cols-2 gap-1 text-[10px] text-muted-foreground">
          <span>Start frame:</span>
          <span className="text-foreground">{item.from}</span>
          <span>Duration:</span>
          <span className="text-foreground">{item.durationInFrames}f</span>
        </div>
      </div>
    </div>
  );
}
