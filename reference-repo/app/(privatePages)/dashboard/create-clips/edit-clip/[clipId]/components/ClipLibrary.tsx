"use client";

import { useState, useMemo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Image from "next/image";
import { Film, Plus, Search, Check } from "lucide-react";
import { observer } from "@legendapp/state/react";
import type { PlayerRef } from "@remotion/player";
import type { SessionClipForEditor } from "@/types/remotionEditor";
import { addVideoItem, editor$, parseTimestampToMs } from "@/stores/editorStore";

interface ClipLibraryProps {
  sessionClips: SessionClipForEditor[];
  fullVideoUrl: string | null;
  mainMpId: number;
  playerRef: React.RefObject<PlayerRef | null>;
  sessionLengthSeconds: number | null;
}

function formatDuration(startTs: string, endTs: string): string {
  const startMs = parseTimestampToMs(startTs);
  const endMs = parseTimestampToMs(endTs);
  const durationSec = Math.round((endMs - startMs) / 1000);
  const m = Math.floor(durationSec / 60);
  const s = durationSec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

type SortOption = "time" | "duration";
type FilterTab = "my-mp" | "all";

function ClipLibraryInner({
  sessionClips,
  fullVideoUrl,
  mainMpId,
  playerRef,
  sessionLengthSeconds,
}: ClipLibraryProps) {
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("time");
  const [filterTab, setFilterTab] = useState<FilterTab>("my-mp");

  const filteredClips = useMemo(() => {
    let clips = [...sessionClips];

    // Filter by MP
    if (filterTab === "my-mp") {
      clips = clips.filter((c) => c.member_id === mainMpId);
    }

    // Search by name and transcript
    if (search.trim()) {
      const q = search.toLowerCase();
      clips = clips.filter(
        (c) =>
          String(c.member_id).includes(q) ||
          (c.parliament_members?.display_name ?? "").toLowerCase().includes(q) ||
          (c.description ?? "").toLowerCase().includes(q) ||
          (c.transcript ?? "").toLowerCase().includes(q)
      );
    }

    // Sort
    if (sortBy === "time") {
      clips.sort(
        (a, b) =>
          parseTimestampToMs(a.start_timestamp) - parseTimestampToMs(b.start_timestamp)
      );
    } else {
      clips.sort((a, b) => {
        const durA =
          parseTimestampToMs(a.end_timestamp) - parseTimestampToMs(a.start_timestamp);
        const durB =
          parseTimestampToMs(b.end_timestamp) - parseTimestampToMs(b.start_timestamp);
        return durB - durA;
      });
    }

    return clips;
  }, [sessionClips, search, sortBy, filterTab, mainMpId]);

  const handleInsertClip = useCallback(
    (clip: SessionClipForEditor) => {
      if (!fullVideoUrl) return;

      const startMs = parseTimestampToMs(clip.start_timestamp);
      const endMs = parseTimestampToMs(clip.end_timestamp);
      const durationSeconds = (endMs - startMs) / 1000;

      // Insert into the selected track if it's a video track, otherwise last video track
      const selectedTrackId = editor$.selectedTrackId.peek();
      const tracks = editor$.tracks.peek();
      const selectedTrack = selectedTrackId
        ? tracks.find((t) => t.id === selectedTrackId && t.type === "video")
        : null;
      const targetTrackId = selectedTrack ? selectedTrackId ?? undefined : undefined;

      const newItem = addVideoItem({
        src: fullVideoUrl,
        clipId: clip.id,
        startTimestamp: clip.start_timestamp,
        endTimestamp: clip.end_timestamp,
        sessionDurationMs: (sessionLengthSeconds ?? 0) * 1000,
        mpName: clip.parliament_members?.display_name ?? "Unknown MP",
        transcript: clip.transcript ?? "",
        thumbnailUrl: clip.thumbnail_url,
        durationSeconds,
        targetTrackId,
      });

      // If we inserted, seek the player to the new item's end
      if (newItem && playerRef.current) {
        const endFrame = newItem.from + newItem.durationInFrames;
        playerRef.current.seekTo(endFrame);
      }
    },
    [fullVideoUrl, playerRef, sessionLengthSeconds]
  );

  // Check which clip IDs are already on the timeline (reactive via observer)
  const tracks = editor$.tracks.get();
  const addedClipIds = useMemo(() => {
    const ids = new Set<string>();
    for (const track of tracks) {
      for (const item of track.items) {
        if (item.sourceClip?.clipId) {
          ids.add(item.sourceClip.clipId);
        }
      }
    }
    return ids;
  }, [tracks]);

  return (
    <div className="flex flex-col h-full">
      {/* Filter tabs */}
      <div className="flex-shrink-0 px-3 pt-2.5 pb-2">
        <ToggleGroup
          type="single"
          value={filterTab}
          onValueChange={(v) => { if (v) setFilterTab(v as FilterTab); }}
          variant="outline"
          className="w-full"
        >
          <ToggleGroupItem value="my-mp" className="text-xs h-7">
            My MP
          </ToggleGroupItem>
          <ToggleGroupItem value="all" className="text-xs h-7">
            All MPs
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Search */}
      <div className="flex-shrink-0 px-3 pb-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search clips..."
            className="h-8 pl-8 text-xs"
          />
        </div>
      </div>

      {/* Sort + count */}
      <div className="flex-shrink-0 px-3 pb-2 flex items-center gap-2">
        <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
          <SelectTrigger className="h-7 w-[110px] text-xs">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="time">Sort: Time</SelectItem>
            <SelectItem value="duration">Sort: Duration</SelectItem>
          </SelectContent>
        </Select>
        <Badge variant="secondary" className="ml-auto text-[10px] h-5">
          {filteredClips.length} clip{filteredClips.length !== 1 ? "s" : ""}
        </Badge>
      </div>

      {/* Clip list */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="px-3 pb-3 space-y-1.5">
          {filteredClips.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <Film className="h-10 w-10 text-muted-foreground/50" />
              <p className="text-xs font-medium text-muted-foreground">
                No clips found
              </p>
              <p className="text-[10px] text-muted-foreground/70">
                Try adjusting your search or filter
              </p>
            </div>
          )}
          {filteredClips.map((clip) => (
            <ClipCard
              key={clip.id}
              clip={clip}
              onInsert={handleInsertClip}
              disabled={!fullVideoUrl}
              isAdded={addedClipIds.has(clip.id)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

export const ClipLibrary = observer(ClipLibraryInner);

// ─── ClipCard ────────────────────────────────────────────────────────────────

interface ClipCardProps {
  clip: SessionClipForEditor;
  onInsert: (clip: SessionClipForEditor) => void;
  disabled: boolean;
  isAdded: boolean;
}

function ClipCard({ clip, onInsert, disabled, isAdded }: ClipCardProps) {
  const mpName = clip.parliament_members?.display_name ?? "Unknown MP";
  const duration = formatDuration(clip.start_timestamp, clip.end_timestamp);
  const transcript = clip.transcript ?? "";

  return (
    <div className="group relative rounded-md border border-border bg-background p-2 hover:border-primary/50 transition-colors">
      <div className="flex gap-2">
        {/* Thumbnail */}
        {clip.thumbnail_url ? (
          <Image
            src={clip.thumbnail_url}
            alt={mpName}
            width={80}
            height={48}
            className="w-20 h-12 rounded object-cover flex-shrink-0 bg-muted"
          />
        ) : (
          <div className="w-20 h-12 rounded bg-muted flex-shrink-0 flex items-center justify-center">
            <Film className="h-4 w-4 text-muted-foreground" />
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between pr-8">
            <p className="text-xs font-medium truncate">{mpName}</p>
            <span className="text-[10px] text-muted-foreground flex-shrink-0 ml-1">
              {duration}
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground line-clamp-2 mt-0.5">
            {transcript || "No transcript"}
          </p>
        </div>
      </div>

      {/* Insert button — always visible for touch/accessibility */}
      <div className="absolute top-1.5 right-1.5 flex items-center gap-1">
        {isAdded && (
          <Badge variant="secondary" className="h-5 text-[9px] gap-0.5 px-1.5">
            <Check className="h-2.5 w-2.5" />
            Added
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => onInsert(clip)}
          disabled={disabled}
          aria-label="Insert clip"
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
