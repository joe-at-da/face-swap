export type Corner = "top-left" | "top-right" | "bottom-left" | "bottom-right";

export const CORNER_CURSORS: Record<Corner, string> = {
  "top-left": "nwse-resize",
  "top-right": "nesw-resize",
  "bottom-left": "nesw-resize",
  "bottom-right": "nwse-resize",
};

export function cornerHandleStyle(
  corner: Corner,
  handleSize: number
): React.CSSProperties {
  const half = -handleSize / 2;
  const base: React.CSSProperties = {
    position: "absolute",
    width: handleSize,
    height: handleSize,
    backgroundColor: "#ffffff",
    border: "1px solid hsl(var(--primary))",
    borderRadius: 2,
    pointerEvents: "auto",
    zIndex: 21,
    cursor: CORNER_CURSORS[corner],
  };
  switch (corner) {
    case "top-left":
      return { ...base, top: half, left: half };
    case "top-right":
      return { ...base, top: half, right: half };
    case "bottom-left":
      return { ...base, bottom: half, left: half };
    case "bottom-right":
      return { ...base, bottom: half, right: half };
  }
}
