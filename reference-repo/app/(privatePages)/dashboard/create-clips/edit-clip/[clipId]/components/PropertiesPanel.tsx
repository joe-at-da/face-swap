"use client";

import { useCallback, useState, useRef, useEffect } from "react";
import { observer } from "@legendapp/state/react";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { editor$, updateItemProperties } from "@/stores/editorStore";
import type { TimelineItem, TextAnimation } from "@/types/remotionEditor";
import { VideoPropertiesPanel } from "./VideoPropertiesPanel";
import { ImagePropertiesPanel } from "./ImagePropertiesPanel";
import { ColorPickerPopover } from "./ColorPickerPopover";

interface PropertiesPanelProps {
  itemId: string;
}

function PropertiesPanelInner({ itemId }: PropertiesPanelProps) {
  const tracks = editor$.tracks.get();

  // No useMemo — Legend State's .get() returns the same parent reference on
  // nested changes, which would cause useMemo to return a stale cached item.
  let item: TimelineItem | null = null;
  for (const track of tracks) {
    const found = track.items.find((i) => i.id === itemId);
    if (found) {
      item = found;
      break;
    }
  }

  if (!item) {
    return (
      <div className="p-4 text-xs text-muted-foreground">
        Item not found.
      </div>
    );
  }

  if (item.type === "video") {
    return <VideoPropertiesPanel item={item} />;
  }

  if (item.type === "image") {
    return <ImagePropertiesPanel item={item} />;
  }

  if (item.type === "text") {
    return <TextProperties item={item} />;
  }

  return (
    <div className="p-4 text-xs text-muted-foreground">
      No properties available for this item type.
    </div>
  );
}

export const PropertiesPanel = observer(PropertiesPanelInner);

// ─── Text Properties ─────────────────────────────────────────────────────────

function TextProperties({ item }: { item: TimelineItem }) {
  // Use local state to prevent focus loss from store updates on every keystroke
  const [localText, setLocalText] = useState(item.text ?? "");
  const [localFontSize, setLocalFontSize] = useState(item.fontSize ?? 48);
  const itemIdRef = useRef(item.id);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Sync local state when item changes or text is updated externally (e.g. inline editor)
  useEffect(() => {
    const isOwnInputFocused = document.activeElement === inputRef.current;
    if (!isOwnInputFocused) {
      setLocalText(item.text ?? "");
    }
    setLocalFontSize(item.fontSize ?? 48);
    itemIdRef.current = item.id;
  }, [item.id, item.text, item.fontSize]);

  const handleTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setLocalText(e.target.value);
    },
    []
  );

  const handleTextBlur = useCallback(() => {
    if (localText !== (item.text ?? "")) {
      updateItemProperties(item.id, { text: localText });
    }
  }, [item.id, item.text, localText]);

  const handleTextKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      e.stopPropagation(); // Prevent keyboard shortcuts while typing
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        updateItemProperties(item.id, { text: localText });
        (e.target as HTMLTextAreaElement).blur();
      }
    },
    [item.id, localText]
  );

  const handleFontSizeCommit = useCallback(
    (value: number[]) => {
      updateItemProperties(item.id, { fontSize: value[0] });
    },
    [item.id]
  );

  const handleColorChange = useCallback(
    (hex: string) => {
      updateItemProperties(item.id, { color: hex });
    },
    [item.id]
  );

  const handleBgColorChange = useCallback(
    (hex: string) => {
      updateItemProperties(item.id, { backgroundColor: hex });
    },
    [item.id]
  );

  const handleFontFamilyChange = useCallback(
    (value: string) => {
      updateItemProperties(item.id, { fontFamily: value });
    },
    [item.id]
  );

  const handleAnimationChange = useCallback(
    (value: string) => {
      updateItemProperties(item.id, {
        animation: value as TextAnimation,
      });
    },
    [item.id]
  );

  return (
    <div className="p-3 space-y-4">
      {/* Text content */}
      <div className="space-y-1.5">
        <Label className="text-xs">Text</Label>
        <Textarea
          ref={inputRef}
          value={localText}
          onChange={handleTextChange}
          onBlur={handleTextBlur}
          onKeyDown={handleTextKeyDown}
          className="min-h-[60px] text-xs resize-none"
        />
      </div>

      {/* Font size */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label className="text-xs">Font size</Label>
          <span className="text-[10px] text-muted-foreground">
            {localFontSize}px
          </span>
        </div>
        <Slider
          value={[localFontSize]}
          min={12}
          max={200}
          step={2}
          onValueChange={(v) => setLocalFontSize(v[0])}
          onValueCommit={handleFontSizeCommit}
        />
      </div>

      {/* Font family */}
      <div className="space-y-1.5">
        <Label className="text-xs">Font</Label>
        <Select
          value={item.fontFamily ?? "Inter"}
          onValueChange={handleFontFamilyChange}
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Inter">Inter</SelectItem>
            <SelectItem value="Arial">Arial</SelectItem>
            <SelectItem value="Georgia">Georgia</SelectItem>
            <SelectItem value="Courier New">Courier New</SelectItem>
            <SelectItem value="Impact">Impact</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Colors */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Color</Label>
          <ColorPickerPopover
            value={item.color ?? "#ffffff"}
            onChange={handleColorChange}
            label="Text color"
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Background</Label>
          <ColorPickerPopover
            value={
              item.backgroundColor === "transparent"
                ? "#000000"
                : item.backgroundColor ?? "#000000"
            }
            onChange={handleBgColorChange}
            label="Background color"
          />
        </div>
      </div>

      {/* Animation */}
      <div className="space-y-1.5">
        <Label className="text-xs">Animation</Label>
        <Select
          value={item.animation ?? "none"}
          onValueChange={handleAnimationChange}
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            <SelectItem value="fade-in">Fade In</SelectItem>
            <SelectItem value="slide-in-left">Slide In Left</SelectItem>
            <SelectItem value="slide-in-right">Slide In Right</SelectItem>
            <SelectItem value="typewriter">Typewriter</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Position info */}
      <div className="pt-2 border-t border-border space-y-1">
        <p className="text-[10px] text-muted-foreground font-medium">
          Position
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
