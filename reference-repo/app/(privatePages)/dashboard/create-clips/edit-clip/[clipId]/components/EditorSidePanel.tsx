"use client";

import { observer } from "@legendapp/state/react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Film, Type, ImageIcon, Captions, Download } from "lucide-react";
import { editor$, selectItem } from "@/stores/editorStore";
import type { PlayerRef } from "@remotion/player";
import type { SessionClipForEditor } from "@/types/remotionEditor";
import { ClipLibrary } from "./ClipLibrary";
import { PropertiesPanel } from "./PropertiesPanel";
import { TextPresetsTab } from "./TextPresetsTab";
import { SubtitlesTab } from "./SubtitlesTab";
import { ImagesTab } from "./ImagesTab";
import { ExportTab } from "./ExportTab";

interface EditorSidePanelProps {
  sessionClips: SessionClipForEditor[];
  fullVideoUrl: string | null;
  mainMpId: number;
  playerRef: React.RefObject<PlayerRef | null>;
  sessionLengthSeconds: number | null;
}

function EditorSidePanelInner({
  sessionClips,
  fullVideoUrl,
  mainMpId,
  playerRef,
  sessionLengthSeconds,
}: EditorSidePanelProps) {
  const selectedItemId = editor$.selectedItemId.get();

  // When an item is selected, show Properties Panel
  if (selectedItemId) {
    return (
      <div className="flex flex-col h-full bg-card">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => selectItem(null)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">Properties</span>
        </div>
        <div className="flex-1 overflow-y-auto">
          <PropertiesPanel itemId={selectedItemId} />
        </div>
      </div>
    );
  }

  // Default: Asset Browser with tabs
  return (
    <div className="flex flex-col h-full bg-card">
      <Tabs defaultValue="media" className="flex flex-col h-full">
        <TabsList className="flex-shrink-0 w-full rounded-none border-b border-border bg-transparent h-auto p-0">
          <TabsTrigger
            value="media"
            className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent py-2 text-xs gap-1"
          >
            <Film className="h-3.5 w-3.5" />
            Media
          </TabsTrigger>
          <TabsTrigger
            value="text"
            className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent py-2 text-xs gap-1"
          >
            <Type className="h-3.5 w-3.5" />
            Text
          </TabsTrigger>
          <TabsTrigger
            value="images"
            className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent py-2 text-xs gap-1"
          >
            <ImageIcon className="h-3.5 w-3.5" />
            Images
          </TabsTrigger>
          <TabsTrigger
            value="subtitles"
            className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent py-2 text-xs gap-1"
          >
            <Captions className="h-3.5 w-3.5" />
            Subtitles
          </TabsTrigger>
          <TabsTrigger
            value="export"
            className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent py-2 text-xs gap-1"
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </TabsTrigger>
        </TabsList>

        <TabsContent value="media" className="flex-1 overflow-hidden mt-0">
          <ClipLibrary
            sessionClips={sessionClips}
            fullVideoUrl={fullVideoUrl}
            mainMpId={mainMpId}
            playerRef={playerRef}
            sessionLengthSeconds={sessionLengthSeconds}
          />
        </TabsContent>

        <TabsContent value="text" className="flex-1 overflow-hidden mt-0">
          <TextPresetsTab />
        </TabsContent>

        <TabsContent value="images" className="flex-1 overflow-hidden mt-0">
          <ImagesTab />
        </TabsContent>

        <TabsContent value="subtitles" className="flex-1 overflow-hidden mt-0">
          <SubtitlesTab />
        </TabsContent>

        <TabsContent value="export" className="flex-1 overflow-hidden mt-0">
          <ExportTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const EditorSidePanel = observer(EditorSidePanelInner);
