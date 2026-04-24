import { useCurrentFrame, useVideoConfig, Img } from "remotion";
import type { TimelineItem } from "@/types/remotionEditor";
import { computeOverlayAnimation } from "./animationUtils";

interface ImageOverlayProps {
  item: TimelineItem;
}

/**
 * Image overlay component with frame-based animations.
 * Position uses percentage values (0-1) relative to composition dimensions.
 * Sizing uses imageWidthPercent (% of composition width), height auto for aspect ratio.
 * All animations use useCurrentFrame() + interpolate() — NO CSS animations.
 */
export const ImageOverlay: React.FC<ImageOverlayProps> = ({ item }) => {
  const frame = useCurrentFrame();
  const { fps, width: compositionWidth } = useVideoConfig();

  if (!item.src) return null;

  const animation = item.animation ?? "none";
  const transform = item.transform ?? {};
  const scale = transform.scale ?? 1;
  const rotation = transform.rotation ?? 0;

  const { opacity, translateX } = computeOverlayAnimation(
    animation,
    frame,
    fps,
    item.opacity ?? 1
  );

  // Build transform string
  const transformParts: string[] = ["translate(-50%, -50%)"];
  if (translateX !== 0) transformParts.push(`translateX(${translateX}px)`);
  if (scale !== 1) transformParts.push(`scale(${scale})`);
  if (rotation !== 0) transformParts.push(`rotate(${rotation}deg)`);
  if (item.flipH) transformParts.push("scaleX(-1)");
  if (item.flipV) transformParts.push("scaleY(-1)");

  const imgWidth = ((item.imageWidthPercent ?? 30) / 100) * compositionWidth;

  return (
    <div
      style={{
        position: "absolute",
        left: `${(item.position?.x ?? 0.5) * 100}%`,
        top: `${(item.position?.y ?? 0.5) * 100}%`,
        transform: transformParts.join(" "),
        opacity,
        pointerEvents: "none",
      }}
    >
      <Img
        src={item.src}
        style={{
          width: imgWidth,
          height: "auto",
          objectFit: item.fitMode ?? "contain",
        }}
      />
    </div>
  );
};
