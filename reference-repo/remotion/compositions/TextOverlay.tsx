import { useCurrentFrame, useVideoConfig } from "remotion";
import type { TimelineItem } from "@/types/remotionEditor";
import { computeOverlayAnimation } from "./animationUtils";

interface TextOverlayProps {
  item: TimelineItem;
}

/**
 * Text overlay component with frame-based animations.
 * Position uses percentage values (0-1) relative to composition dimensions.
 * All animations use useCurrentFrame() + interpolate() — NO CSS animations.
 */
export const TextOverlay: React.FC<TextOverlayProps> = ({ item }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!item.text) return null;

  const animation = item.animation ?? "none";

  // Typewriter is a special case — different render output
  if (animation === "typewriter") {
    const text = item.text ?? "";
    const charsPerFrame = 3;
    const visibleChars = Math.min(
      text.length,
      Math.floor(frame * charsPerFrame)
    );
    return (
      <div
        style={{
          position: "absolute",
          left: `${(item.position?.x ?? 0.5) * 100}%`,
          top: `${(item.position?.y ?? 0.5) * 100}%`,
          transform: "translate(-50%, -50%)",
          fontSize: item.fontSize ?? 48,
          fontFamily: item.fontFamily ?? "Inter, sans-serif",
          fontWeight: 700,
          color: item.color ?? "#ffffff",
          backgroundColor: item.backgroundColor ?? "transparent",
          padding: "8px 16px",
          borderRadius: 4,
          whiteSpace: "pre-wrap",
          textAlign: "center",
          maxWidth: "80%",
        }}
      >
        {text.slice(0, visibleChars)}
      </div>
    );
  }

  const { opacity, translateX } = computeOverlayAnimation(
    animation,
    frame,
    fps
  );

  return (
    <div
      style={{
        position: "absolute",
        left: `${(item.position?.x ?? 0.5) * 100}%`,
        top: `${(item.position?.y ?? 0.5) * 100}%`,
        transform: `translate(-50%, -50%) translateX(${translateX}px)`,
        opacity,
        fontSize: item.fontSize ?? 48,
        fontFamily: item.fontFamily ?? "Inter, sans-serif",
        fontWeight: 700,
        color: item.color ?? "#ffffff",
        backgroundColor: item.backgroundColor ?? "transparent",
        padding: "8px 16px",
        borderRadius: 4,
        whiteSpace: "pre-wrap",
        textAlign: "center",
        maxWidth: "80%",
      }}
    >
      {item.text}
    </div>
  );
};
