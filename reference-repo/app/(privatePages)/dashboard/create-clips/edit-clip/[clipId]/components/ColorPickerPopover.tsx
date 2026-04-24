"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ColorPickerPopoverProps {
  value: string;
  onChange: (hex: string) => void;
  label?: string;
}

export function ColorPickerPopover({
  value,
  onChange,
  label,
}: ColorPickerPopoverProps) {
  const [hexInput, setHexInput] = useState(value);

  // Sync hex input when value changes externally (e.g. undo/redo)
  useEffect(() => {
    setHexInput(value);
  }, [value]);

  const handleHexCommit = useCallback(() => {
    const cleaned = hexInput.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(cleaned)) {
      onChange(cleaned);
    } else {
      setHexInput(value);
    }
  }, [hexInput, onChange, value]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="h-7 w-7 rounded-full border border-border cursor-pointer transition-shadow hover:ring-2 hover:ring-ring/30"
          style={{ backgroundColor: value }}
          aria-label={label ? `Pick ${label} color` : "Pick color"}
        />
      </PopoverTrigger>
      <PopoverContent className="w-48 p-3 space-y-2" align="start">
        {label && (
          <Label className="text-xs font-medium">{label}</Label>
        )}
        <input
          type="color"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setHexInput(e.target.value);
          }}
          className="h-12 w-full rounded border border-border cursor-pointer"
        />
        <Input
          value={hexInput}
          onChange={(e) => setHexInput(e.target.value)}
          onBlur={handleHexCommit}
          onKeyDown={(e) => e.key === "Enter" && handleHexCommit()}
          className="h-7 text-xs font-mono"
          placeholder="#000000"
        />
      </PopoverContent>
    </Popover>
  );
}
