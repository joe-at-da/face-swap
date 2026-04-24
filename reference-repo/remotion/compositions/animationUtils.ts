import { interpolate, spring } from "remotion";
import type { TextAnimation } from "@/types/remotionEditor";

interface AnimationResult {
  opacity: number;
  translateX: number;
}

/**
 * Compute overlay animation values (opacity + translateX) from current frame.
 * Used by TextOverlay and ImageOverlay for consistent animation behavior.
 *
 * @param animation - The animation type
 * @param frame - Current frame from useCurrentFrame()
 * @param fps - FPS from useVideoConfig()
 * @param baseOpacity - Base opacity (default 1, images may pass item.opacity)
 */
export function computeOverlayAnimation(
  animation: TextAnimation,
  frame: number,
  fps: number,
  baseOpacity = 1
): AnimationResult {
  let opacity = baseOpacity;
  let translateX = 0;

  switch (animation) {
    case "fade-in": {
      opacity =
        baseOpacity *
        interpolate(frame, [0, 15], [0, 1], {
          extrapolateRight: "clamp",
        });
      break;
    }
    case "slide-in-left": {
      opacity =
        baseOpacity *
        interpolate(frame, [0, 8], [0, 1], {
          extrapolateRight: "clamp",
        });
      translateX = interpolate(
        spring({ frame, fps, config: { damping: 200, mass: 0.5 } }),
        [0, 1],
        [-200, 0]
      );
      break;
    }
    case "slide-in-right": {
      opacity =
        baseOpacity *
        interpolate(frame, [0, 8], [0, 1], {
          extrapolateRight: "clamp",
        });
      translateX = interpolate(
        spring({ frame, fps, config: { damping: 200, mass: 0.5 } }),
        [0, 1],
        [200, 0]
      );
      break;
    }
    default:
      break;
  }

  return { opacity, translateX };
}
