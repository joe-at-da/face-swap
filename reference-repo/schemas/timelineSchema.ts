import { z } from "zod";
import { session$ } from "@/stores/sessionStore";

// Helper function to parse timestamp (hh:mm:ss.yyy) to seconds
function parseTimestamp(ts: string): number {
  const [timePart, msPart] = ts.split(".");
  const [hours, minutes, seconds] = timePart.split(":").map(Number);
  return hours * 3600 + minutes * 60 + seconds + (msPart ? Number(`0.${msPart}`) : 0);
}

/**
 * Schema for editing timeline item timestamps
 */
export const timelineItemEditSchema = z.object({
  startTimestamp: z.string().regex(/^\d{2}:\d{2}:\d{2}\.\d{3}$/, "Invalid timestamp format (hh:mm:ss.yyy)"),
  endTimestamp: z.string().regex(/^\d{2}:\d{2}:\d{2}\.\d{3}$/, "Invalid timestamp format (hh:mm:ss.yyy)"),
  isMuted: z.boolean(),
}).refine((data) => {
  // Ensure end timestamp is after start timestamp
  const start = parseTimestamp(data.startTimestamp);
  const end = parseTimestamp(data.endTimestamp);

  return end > start;
}, {
  message: "End timestamp must be after start timestamp",
  path: ["endTimestamp"],
}).refine((data) => {
  // Ensure end timestamp doesn't exceed session duration
  const sessionDuration = session$.sessionDuration.peek();

  // Skip validation if session duration not loaded yet
  if (sessionDuration === 0) {
    return true;
  }

  const endSeconds = parseTimestamp(data.endTimestamp);

  if (endSeconds > sessionDuration) {
    return false;
  }

  return true;
}, {
  message: "Cannot extend beyond session end",
  path: ["endTimestamp"],
});

export type TimelineItemEditFormData = z.infer<typeof timelineItemEditSchema>;
