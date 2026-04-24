"use client";

import { useCallback } from "react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { updateItemProperties, updateItemSpeed, peekItem } from "@/stores/editorStore";
import type { TimelineItem, ItemTransform, VideoFilters } from "@/types/remotionEditor";
import { PropertySlider } from "./PropertySlider";
import { EDITOR_FPS } from "@/lib/editorConstants";

// ─── VideoPropertiesPanel ───────────────────────────────────────────────────

interface VideoPropertiesPanelProps {
  item: TimelineItem;
}

export function VideoPropertiesPanel({ item }: VideoPropertiesPanelProps) {
  const mpName = item.sourceClip?.mpName ?? "Video clip";
  const durationSec = (item.durationInFrames / EDITOR_FPS).toFixed(1);

  return (
    <div className="p-3 space-y-4">
      {/* Header */}
      <div>
        <p className="text-sm font-medium">{mpName}</p>
        <p className="text-[10px] text-muted-foreground">{durationSec}s</p>
      </div>

      <SpeedSection item={item} />
      <AudioSection item={item} />
      <TransformSection item={item} />
      <AppearanceSection item={item} />
      <TrimInfoSection item={item} />
    </div>
  );
}

// ─── Speed Section ──────────────────────────────────────────────────────────

function SpeedSection({ item }: { item: TimelineItem }) {
  return (
    <PropertySlider
      label="Speed"
      value={item.playbackRate ?? 1}
      min={0.25}
      max={4}
      step={0.25}
      formatLabel={(v) => `${v.toFixed(2)}x`}
      onCommit={(v) => updateItemSpeed(item.id, v)}
    />
  );
}

// ─── Audio Section ──────────────────────────────────────────────────────────

function AudioSection({ item }: { item: TimelineItem }) {
  const handleMuteToggle = useCallback(
    (checked: boolean) => updateItemProperties(item.id, { isMuted: checked }),
    [item.id]
  );

  return (
    <div className="space-y-3">
      <PropertySlider
        label="Volume"
        value={item.volume ?? 1}
        min={0}
        max={1}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => updateItemProperties(item.id, { volume: v })}
      />

      {/* Mute */}
      <div className="flex items-center justify-between">
        <Label className="text-xs">Mute audio</Label>
        <Switch
          checked={item.isMuted ?? false}
          onCheckedChange={handleMuteToggle}
        />
      </div>

      <PropertySlider
        label="Fade In"
        value={item.audioFadeIn ?? 0}
        min={0}
        max={60}
        step={1}
        formatLabel={(v) => `${(v / EDITOR_FPS).toFixed(1)}s`}
        onCommit={(v) => updateItemProperties(item.id, { audioFadeIn: v })}
      />

      <PropertySlider
        label="Fade Out"
        value={item.audioFadeOut ?? 0}
        min={0}
        max={60}
        step={1}
        formatLabel={(v) => `${(v / EDITOR_FPS).toFixed(1)}s`}
        onCommit={(v) => updateItemProperties(item.id, { audioFadeOut: v })}
      />
    </div>
  );
}

// ─── Transform Section ──────────────────────────────────────────────────────

function TransformSection({ item }: { item: TimelineItem }) {
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
    <div className="pt-2 border-t border-border space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium">Transform</p>
        <button
          onClick={handleResetTransform}
          className="text-[10px] text-muted-foreground hover:text-foreground"
        >
          Reset
        </button>
      </div>

      <PropertySlider
        label="Zoom"
        value={t.scale ?? 1}
        min={0.5}
        max={4}
        step={0.1}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => handleTransformCommit("scale", v)}
      />

      <PropertySlider
        label="Position X"
        value={t.translateX ?? 0}
        min={-100}
        max={100}
        step={1}
        formatLabel={(v) => `${v}%`}
        onCommit={(v) => handleTransformCommit("translateX", v)}
      />

      <PropertySlider
        label="Position Y"
        value={t.translateY ?? 0}
        min={-100}
        max={100}
        step={1}
        formatLabel={(v) => `${v}%`}
        onCommit={(v) => handleTransformCommit("translateY", v)}
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
  );
}

// ─── Appearance Section ─────────────────────────────────────────────────────

function AppearanceSection({ item }: { item: TimelineItem }) {
  const f = item.filters ?? {};

  const handleFilterCommit = useCallback(
    (key: keyof VideoFilters, value: number) => {
      const current = peekItem(item.id)?.filters ?? {};
      updateItemProperties(item.id, {
        filters: { ...current, [key]: value },
      });
    },
    [item.id]
  );

  const handleResetAppearance = useCallback(() => {
    updateItemProperties(item.id, {
      opacity: undefined,
      filters: undefined,
    });
  }, [item.id]);

  return (
    <div className="pt-2 border-t border-border space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium">Appearance</p>
        <button
          onClick={handleResetAppearance}
          className="text-[10px] text-muted-foreground hover:text-foreground"
        >
          Reset
        </button>
      </div>

      <PropertySlider
        label="Opacity"
        value={item.opacity ?? 1}
        min={0}
        max={1}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => updateItemProperties(item.id, { opacity: v })}
      />

      <PropertySlider
        label="Brightness"
        value={f.brightness ?? 1}
        min={0}
        max={2}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => handleFilterCommit("brightness", v)}
      />

      <PropertySlider
        label="Contrast"
        value={f.contrast ?? 1}
        min={0}
        max={2}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => handleFilterCommit("contrast", v)}
      />

      <PropertySlider
        label="Saturation"
        value={f.saturation ?? 1}
        min={0}
        max={2}
        step={0.05}
        formatLabel={(v) => `${Math.round(v * 100)}%`}
        onCommit={(v) => handleFilterCommit("saturation", v)}
      />
    </div>
  );
}

// ─── Trim Info Section ──────────────────────────────────────────────────────

function TrimInfoSection({ item }: { item: TimelineItem }) {
  return (
    <div className="pt-2 border-t border-border space-y-1">
      <p className="text-[10px] text-muted-foreground font-medium">
        Trim Info
      </p>
      <div className="grid grid-cols-2 gap-1 text-[10px] text-muted-foreground">
        <span>Start frame:</span>
        <span className="text-foreground">{item.from}</span>
        <span>Duration:</span>
        <span className="text-foreground">{item.durationInFrames}f</span>
        {item.startFrom != null && (
          <>
            <span>Source offset:</span>
            <span className="text-foreground">{item.startFrom}f</span>
          </>
        )}
      </div>
    </div>
  );
}
