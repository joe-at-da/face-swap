"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

/**
 * Slider that tracks local state during drag for smooth UI updates.
 * Store is only updated on commit (release) to avoid 60fps Remotion re-renders.
 */
export function PropertySlider({
  label,
  value: externalValue,
  min,
  max,
  step,
  formatLabel,
  onCommit,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  formatLabel: (v: number) => string;
  onCommit: (v: number) => void;
}) {
  const [localValue, setLocalValue] = useState(externalValue);

  // Sync when store value changes externally (undo/redo, reset)
  useEffect(() => {
    setLocalValue(externalValue);
  }, [externalValue]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="text-[10px] text-muted-foreground">
          {formatLabel(localValue)}
        </span>
      </div>
      <Slider
        value={[localValue]}
        min={min}
        max={max}
        step={step}
        onValueChange={(v) => setLocalValue(v[0])}
        onValueCommit={(v) => onCommit(v[0])}
      />
    </div>
  );
}
