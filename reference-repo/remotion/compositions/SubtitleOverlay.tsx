import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { createTikTokStyleCaptions } from "@remotion/captions";
import type { SubtitleTrack } from "@/types/remotionEditor";

/**
 * Subtitle overlay with word-level TikTok-style highlighting.
 * Uses @remotion/captions to group words into pages and highlight
 * the currently spoken word.
 */
interface SubtitleOverlayProps extends SubtitleTrack {
  videoTransform?: { scale: number; translateX: number; translateY: number };
}

export const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({
  captions,
  style,
  videoTransform,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  // Group captions into pages using @remotion/captions
  const { pages } = useMemo(
    () =>
      createTikTokStyleCaptions({
        captions,
        combineTokensWithinMilliseconds: 10000,
      }),
    [captions]
  );

  // Enforce maxWordsPerLine by splitting large pages into smaller sub-pages
  const splitPages = useMemo(() => {
    const maxWords = style.maxWordsPerLine;
    const result: typeof pages = [];
    for (const page of pages) {
      if (page.tokens.length <= maxWords) {
        result.push(page);
      } else {
        for (let i = 0; i < page.tokens.length; i += maxWords) {
          const chunk = page.tokens.slice(i, i + maxWords);
          const firstToken = chunk[0];
          const lastToken = chunk[chunk.length - 1];
          result.push({
            text: chunk.map((t) => t.text).join(" "),
            startMs: firstToken.fromMs,
            durationMs: lastToken.toMs - firstToken.fromMs,
            tokens: chunk,
          });
        }
      }
    }
    return result;
  }, [pages, style.maxWordsPerLine]);

  // Find the active page at the current time
  const activePage = splitPages.find((page) => {
    const pageEndMs = page.startMs + page.durationMs;
    return currentTimeMs >= page.startMs && currentTimeMs < pageEndMs;
  });

  if (!activePage) return null;

  // Position relative to the video's visual bounds (from its CSS transform)
  const s = videoTransform?.scale ?? 1;
  const tx = videoTransform?.translateX ?? 0;
  const ty = videoTransform?.translateY ?? 0;

  const positionStyle: React.CSSProperties = {};
  if (style.position === "bottom") {
    // 10% of video height up from video's bottom edge
    positionStyle.bottom = `${50 - ty - 40 * s}%`;
  } else if (style.position === "top") {
    // 10% of video height down from video's top edge
    positionStyle.top = `${50 + ty - 40 * s}%`;
  } else {
    // Center of video
    positionStyle.top = `${50 + ty}%`;
    positionStyle.transform = "translateY(-50%)";
  }

  // Constrain horizontal bounds to video's visual area
  const leftPercent = 50 + tx - 50 * s;
  const rightPercent = 50 - tx - 50 * s;

  // Text shadow for outline effect
  const textShadow =
    style.outlineWidth && style.outlineColor
      ? `${style.outlineColor} 0px 0px ${style.outlineWidth}px, ${style.outlineColor} 0px 0px ${style.outlineWidth * 2}px`
      : undefined;

  return (
    <div
      style={{
        position: "absolute",
        left: `${leftPercent}%`,
        right: `${rightPercent}%`,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        padding: `0 ${5 * s}%`,
        ...positionStyle,
      }}
    >
      <div
        style={{
          backgroundColor: style.backgroundColor,
          padding: "8px 16px",
          borderRadius: 6,
          textAlign: "center",
          maxWidth: "90%",
        }}
      >
        {activePage.tokens.map((token, i) => {
          const isActive =
            currentTimeMs >= token.fromMs && currentTimeMs < token.toMs;

          return (
            <span
              key={`${token.fromMs}-${i}`}
              style={{
                fontSize: style.fontSize,
                fontFamily: style.fontFamily,
                fontWeight: 700,
                color: style.highlightEnabled && isActive ? style.highlightColor : style.color,
                textShadow,
                transition: "none", // No CSS transitions in Remotion
              }}
            >
              {token.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};
