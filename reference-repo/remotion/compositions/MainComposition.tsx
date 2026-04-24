import { AbsoluteFill, Sequence } from "remotion";
import type { Track, SubtitleTrack, TimelineItem } from "@/types/remotionEditor";
import { ClipSequence } from "./ClipSequence";
import { SubtitleOverlay } from "./SubtitleOverlay";
import { TextOverlay } from "./TextOverlay";
import { ImageOverlay } from "./ImageOverlay";
import { SequenceErrorBoundary } from "./SequenceErrorBoundary";

/** Count how many earlier videoItems overlap temporally with the item at `index`. */
function getOverlapRank(items: TimelineItem[], index: number): number {
  let rank = 0;
  const item = items[index];
  const itemEnd = item.from + item.durationInFrames;
  for (let j = 0; j < index; j++) {
    const otherEnd = items[j].from + items[j].durationInFrames;
    if (item.from < otherEnd && items[j].from < itemEnd) {
      rank++;
    }
  }
  return rank;
}

export interface MainCompositionProps {
  tracks: Track[];
  subtitlesByItemId: Record<string, SubtitleTrack>;
  inlineEditItemId?: string | null;
}

/**
 * Root Remotion composition.
 *
 * Renders layers bottom-to-top:
 * 1. Video tracks + subtitles (bottom)
 * 2. Image overlays
 * 3. Text overlays (top)
 */
export const MainComposition: React.FC<MainCompositionProps> = ({
  tracks,
  subtitlesByItemId,
  inlineEditItemId,
}) => {
  const videoItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "video")
  );
  const imageItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "image")
  );
  const textItems = tracks.flatMap((t) =>
    t.items.filter((i) => i.type === "text")
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Layer 1: Video items with per-video subtitles */}
      {videoItems.map((item, i) => (
        <Sequence
          key={item.id}
          from={item.from}
          durationInFrames={item.durationInFrames}
          premountFor={150}
        >
          <SequenceErrorBoundary itemId={item.id}>
            <ClipSequence item={item} seekDelay={getOverlapRank(videoItems, i) * 500} />
          </SequenceErrorBoundary>
          {subtitlesByItemId[item.id] && (
            <SubtitleOverlay
              {...subtitlesByItemId[item.id]}
              videoTransform={{
                scale: item.transform?.scale ?? 1,
                translateX: item.transform?.translateX ?? 0,
                translateY: item.transform?.translateY ?? 0,
              }}
            />
          )}
        </Sequence>
      ))}

      {/* Layer 2: Image overlays */}
      {imageItems.map((item) => (
        <Sequence
          key={item.id}
          from={item.from}
          durationInFrames={item.durationInFrames}
          premountFor={30}
        >
          <ImageOverlay item={item} />
        </Sequence>
      ))}

      {/* Layer 3: Text overlays (hide the item being inline-edited) */}
      {textItems
        .filter((item) => item.id !== inlineEditItemId)
        .map((item) => (
          <Sequence
            key={item.id}
            from={item.from}
            durationInFrames={item.durationInFrames}
          >
            <TextOverlay item={item} />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
};
