"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { observer } from "@legendapp/state/react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Captions, CheckCircle2, Video, X } from "lucide-react";
import { editor$ } from "@/stores/editorStore";
import {
  subtitle$,
  DEFAULT_STYLE,
  setCaptions,
  setGenerating,
  updateItemSubtitleStyle,
  updateCaptionText,
  deleteCaption,
} from "@/stores/subtitleStore";
import { generateSubtitles } from "@/app/actions/generateSubtitles";
import type { Caption, SubtitleStyle, TimelineItem } from "@/types/remotionEditor";
import { Switch } from "@/components/ui/switch";
import { ColorPickerPopover } from "./ColorPickerPopover";
import { EDITOR_FPS } from "@/lib/editorConstants";

/** Compute the source video time range for a timeline item. */
function getSourceTimeRange(item: TimelineItem): { startMs: number; endMs: number } {
  const startMs = ((item.startFrom ?? 0) / EDITOR_FPS) * 1000;
  const sourceFrameDuration =
    item.endAt != null
      ? item.endAt - (item.startFrom ?? 0)
      : item.durationInFrames * (item.playbackRate || 1);
  const endMs = startMs + (sourceFrameDuration / EDITOR_FPS) * 1000;
  return { startMs, endMs };
}

// ─── Caption Editor ─────────────────────────────────────────────────────────

function formatMs(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

function CaptionEditor({
  itemId,
  captions,
}: {
  itemId: string;
  captions: Caption[];
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingIndex !== null && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingIndex]);

  const handleStartEdit = useCallback((index: number, text: string) => {
    setEditingIndex(index);
    setEditText(text);
  }, []);

  const handleCommit = useCallback(() => {
    if (editingIndex === null) return;
    const originalText = captions[editingIndex]?.text ?? "";
    const hadLeadingSpace = originalText.startsWith(" ");
    const trimmed = editText.trim();
    if (!trimmed) { setEditingIndex(null); return; }
    const committed = hadLeadingSpace ? " " + trimmed : trimmed;
    if (committed !== originalText) {
      updateCaptionText(itemId, editingIndex, committed);
    }
    setEditingIndex(null);
  }, [editingIndex, editText, itemId, captions]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === "Enter") {
        handleCommit();
      } else if (e.key === "Escape") {
        setEditingIndex(null);
      }
    },
    [handleCommit]
  );

  const handleDelete = useCallback(
    (index: number) => {
      deleteCaption(itemId, index);
      if (editingIndex === index) setEditingIndex(null);
    },
    [itemId, editingIndex]
  );

  if (captions.length === 0) return null;

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-foreground">Captions</p>
      <div className="space-y-0.5 max-h-48 overflow-y-auto rounded border border-border p-1">
        {captions.map((cap, i) => (
          <div key={i} className="flex items-center gap-1 group">
            <span className="text-[10px] text-muted-foreground shrink-0 w-8 tabular-nums">
              {formatMs(cap.startMs)}
            </span>
            {editingIndex === i ? (
              <input
                ref={inputRef}
                type="text"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onBlur={handleCommit}
                onKeyDown={handleKeyDown}
                className="flex-1 h-5 text-xs bg-accent border border-input rounded px-1 outline-none"
              />
            ) : (
              <button
                type="button"
                onClick={() => handleStartEdit(i, cap.text)}
                className="flex-1 text-left text-xs truncate hover:bg-accent rounded px-1 h-5"
              >
                {cap.text}
              </button>
            )}
            <button
              type="button"
              onClick={() => handleDelete(i)}
              className="text-muted-foreground hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Tab ───────────────────────────────────────────────────────────────

function SubtitlesTabInner() {
  const [isPending, startTransition] = useTransition();
  const selectedItemId = editor$.selectedItemId.get();
  const tracks = editor$.tracks.get();
  const styleByItemId = subtitle$.styleByItemId.get();
  const generatingItemIds = subtitle$.generatingItemIds.get();
  const captionsByItemId = subtitle$.captionsByItemId.get();

  // Local selection within subtitles tab (clicking a clip row)
  const [selectedSubtitleItemId, setSelectedSubtitleItemId] = useState<string | null>(null);

  // Collect all video items across all tracks
  const allVideoItems = useMemo(() => {
    const items: TimelineItem[] = [];
    for (const track of tracks) {
      for (const item of track.items) {
        if (item.type === "video") items.push(item);
      }
    }
    return items;
  }, [tracks]);

  // Find the target video item: prefer subtitle tab selection, then editor selection, then first
  const targetVideoItem = useMemo(() => {
    if (selectedSubtitleItemId) {
      const found = allVideoItems.find((i) => i.id === selectedSubtitleItemId);
      if (found) return found;
    }
    if (selectedItemId) {
      const selected = allVideoItems.find((i) => i.id === selectedItemId);
      if (selected) return selected;
    }
    return allVideoItems[0] ?? null;
  }, [selectedSubtitleItemId, selectedItemId, allVideoItems]);

  const targetItemId = targetVideoItem?.id ?? null;

  // Per-clip style (falls back to DEFAULT_STYLE)
  const style: SubtitleStyle = targetItemId
    ? (styleByItemId[targetItemId] ?? DEFAULT_STYLE)
    : DEFAULT_STYLE;

  // Local state for sliders (smooth dragging)
  const [localFontSize, setLocalFontSize] = useState(style.fontSize);
  const [localOutlineWidth, setLocalOutlineWidth] = useState(style.outlineWidth ?? 0);
  const [localWordsPerLine, setLocalWordsPerLine] = useState(style.maxWordsPerLine);

  // Sync local slider state when target item or its style changes
  useEffect(() => {
    setLocalFontSize(style.fontSize);
    setLocalOutlineWidth(style.outlineWidth ?? 0);
    setLocalWordsPerLine(style.maxWordsPerLine);
  }, [style.fontSize, style.outlineWidth, style.maxWordsPerLine]);

  const hasSubtitles = targetItemId
    ? (captionsByItemId[targetItemId]?.length ?? 0) > 0
    : false;

  const isCurrentlyGenerating = targetItemId
    ? generatingItemIds.includes(targetItemId)
    : false;

  const generateForItem = useCallback(
    (item: TimelineItem) => {
      if (!item.sourceClip) return;
      if (item.isMuted) {
        toast.info("Skipped muted clip", {
          description: "Unmute the clip to generate subtitles",
        });
        return;
      }

      const itemId = item.id;
      const clipId = item.sourceClip.clipId;
      const { startMs, endMs } = getSourceTimeRange(item);

      setGenerating(itemId, true);

      startTransition(async () => {
        try {
          const result = await generateSubtitles(clipId, startMs, endMs);

          if (result.error) {
            toast.error("Subtitle generation failed", {
              description: result.error,
            });
            return;
          }

          setCaptions(itemId, result.captions);
          toast.success("Subtitles generated", {
            description: `${result.captions.length} words transcribed`,
          });
        } catch {
          toast.error("Subtitle generation failed", {
            description: "An unexpected error occurred",
          });
        } finally {
          setGenerating(itemId, false);
        }
      });
    },
    [startTransition]
  );

  const handleGenerate = useCallback(() => {
    if (!targetVideoItem) return;
    generateForItem(targetVideoItem);
  }, [targetVideoItem, generateForItem]);

  const handleGenerateAll = useCallback(async () => {
    if (allVideoItems.length === 0) return;

    const itemsToGenerate = allVideoItems.filter(
      (item) =>
        item.sourceClip &&
        !item.isMuted &&
        !generatingItemIds.includes(item.id)
    );

    if (itemsToGenerate.length === 0) {
      toast.info("No eligible clips to generate subtitles for");
      return;
    }

    // Process sequentially to avoid rate limits and excessive backend load
    let failedCount = 0;
    for (const item of itemsToGenerate) {
      const clipId = item.sourceClip!.clipId;
      const { startMs, endMs } = getSourceTimeRange(item);
      setGenerating(item.id, true);
      try {
        const result = await generateSubtitles(clipId, startMs, endMs);
        if (result.error) {
          failedCount++;
          toast.error(`Subtitles failed for clip ${item.sourceClip?.mpName ?? ""}`, {
            description: result.error,
          });
        } else {
          setCaptions(item.id, result.captions);
        }
      } catch {
        failedCount++;
        toast.error(`Subtitles failed for clip ${item.sourceClip?.mpName ?? ""}`);
      } finally {
        setGenerating(item.id, false);
      }
    }

    if (failedCount === 0) {
      toast.success("All subtitles generated");
    } else if (failedCount < itemsToGenerate.length) {
      toast.warning(`${itemsToGenerate.length - failedCount} of ${itemsToGenerate.length} clips generated`);
    }
  }, [allVideoItems, generatingItemIds]);

  const handleStyleChange = useCallback(
    (key: keyof SubtitleStyle, value: SubtitleStyle[keyof SubtitleStyle]) => {
      if (!targetItemId) return;
      updateItemSubtitleStyle(targetItemId, { [key]: value });
    },
    [targetItemId]
  );

  const isGenerating = isCurrentlyGenerating || isPending;
  const anyGenerating = generatingItemIds.length > 0 || isPending;

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {/* Video items status — clickable to select per-clip settings */}
        {allVideoItems.length > 1 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-foreground">Clips</p>
            <div className="space-y-1">
              {allVideoItems.map((item, idx) => {
                const itemHasSubs = (captionsByItemId[item.id]?.length ?? 0) > 0;
                const itemGenerating = generatingItemIds.includes(item.id);
                const isTarget = item.id === targetItemId;
                return (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => setSelectedSubtitleItemId(item.id)}
                    className={`flex items-center gap-2 px-2 py-1 rounded text-xs w-full text-left transition-colors ${
                      isTarget
                        ? "bg-accent ring-1 ring-ring"
                        : "bg-muted/50 hover:bg-muted"
                    }`}
                  >
                    <Video className="h-3 w-3 text-muted-foreground shrink-0" />
                    <span className="truncate flex-1">
                      Clip {idx + 1}
                      {item.sourceClip?.mpName
                        ? ` - ${item.sourceClip.mpName}`
                        : ""}
                    </span>
                    {itemGenerating ? (
                      <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                    ) : itemHasSubs ? (
                      <CheckCircle2 className="h-3 w-3 text-chart-3" />
                    ) : null}
                  </button>
                );
              })}
            </div>
            <Button
              onClick={handleGenerateAll}
              disabled={anyGenerating}
              variant="outline"
              size="sm"
              className="w-full"
            >
              {anyGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                "Generate All Subtitles"
              )}
            </Button>
            <Separator />
          </div>
        )}

        {/* Generate button for selected/target item */}
        <div className="space-y-2">
          <Button
            onClick={handleGenerate}
            disabled={!targetVideoItem || isGenerating || targetVideoItem?.isMuted}
            className="w-full"
            size="sm"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Captions className="h-4 w-4 mr-2" />
                {hasSubtitles ? "Regenerate Subtitles" : "Generate Subtitles"}
              </>
            )}
          </Button>

          {!targetVideoItem && (
            <p className="text-xs text-muted-foreground text-center">
              Add a video clip to the timeline to generate subtitles.
            </p>
          )}

          {targetVideoItem?.isMuted && (
            <p className="text-xs text-muted-foreground text-center">
              Unmute the clip to generate subtitles.
            </p>
          )}

          {hasSubtitles && targetItemId && !isGenerating && (
            <div className="flex items-center justify-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-chart-3" />
              <p className="text-xs text-muted-foreground">
                {captionsByItemId[targetItemId].length} word
                {captionsByItemId[targetItemId].length !== 1 ? "s" : ""}{" "}
                transcribed
              </p>
            </div>
          )}
        </div>

        {/* Caption list + inline editing */}
        {hasSubtitles && targetItemId && (
          <>
            <CaptionEditor
              itemId={targetItemId}
              captions={captionsByItemId[targetItemId]}
            />
            <Separator />
          </>
        )}

        <Separator />

        {/* Typography section */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-foreground">Typography</p>

          {/* Font size */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Size</Label>
              <span className="text-xs text-muted-foreground">
                {localFontSize}px
              </span>
            </div>
            <Slider
              value={[localFontSize]}
              min={16}
              max={80}
              step={2}
              onValueChange={(v) => setLocalFontSize(v[0])}
              onValueCommit={(v) => handleStyleChange("fontSize", v[0])}
            />
          </div>

          {/* Font family */}
          <div className="space-y-1.5">
            <Label className="text-xs">Font</Label>
            <Select
              value={style.fontFamily}
              onValueChange={(v) => handleStyleChange("fontFamily", v)}
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
        </div>

        <Separator />

        {/* Colors section */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-foreground">Colors</p>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Text color</Label>
              <ColorPickerPopover
                value={style.color}
                onChange={(v) => handleStyleChange("color", v)}
                label="Text color"
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Highlight</Label>
                <Switch
                  checked={style.highlightEnabled}
                  onCheckedChange={(checked) =>
                    handleStyleChange("highlightEnabled", checked)
                  }
                />
              </div>
              {style.highlightEnabled && (
                <ColorPickerPopover
                  value={style.highlightColor}
                  onChange={(v) => handleStyleChange("highlightColor", v)}
                  label="Highlight color"
                />
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Outline color</Label>
              <ColorPickerPopover
                value={style.outlineColor ?? "#000000"}
                onChange={(v) => handleStyleChange("outlineColor", v)}
                label="Outline color"
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Outline</Label>
                <span className="text-xs text-muted-foreground">
                  {localOutlineWidth}px
                </span>
              </div>
              <Slider
                value={[localOutlineWidth]}
                min={0}
                max={6}
                step={1}
                onValueChange={(v) => setLocalOutlineWidth(v[0])}
                onValueCommit={(v) =>
                  handleStyleChange("outlineWidth", v[0])
                }
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Layout section */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-foreground">Layout</p>

          {/* Position */}
          <div className="space-y-1.5">
            <Label className="text-xs">Position</Label>
            <Select
              value={style.position}
              onValueChange={(v) =>
                handleStyleChange(
                  "position",
                  v as "bottom" | "center" | "top"
                )
              }
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="bottom">Bottom</SelectItem>
                <SelectItem value="center">Center</SelectItem>
                <SelectItem value="top">Top</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Max words per line */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Words per line</Label>
              <span className="text-xs text-muted-foreground">
                {localWordsPerLine}
              </span>
            </div>
            <Slider
              value={[localWordsPerLine]}
              min={2}
              max={12}
              step={1}
              onValueChange={(v) => setLocalWordsPerLine(v[0])}
              onValueCommit={(v) =>
                handleStyleChange("maxWordsPerLine", v[0])
              }
            />
          </div>
        </div>
      </div>
    </ScrollArea>
  );
}

export const SubtitlesTab = observer(SubtitlesTabInner);
