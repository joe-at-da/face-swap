import { z } from "zod";

// Bluesky connection schema
export const blueskyConnectionSchema = z.object({
  service: z
    .string()
    .min(1, "Service is required")
    .url("Service must be a valid URL"),
  identifier: z.string().min(1, "Identifier is required").trim(),
  password: z.string().min(1, "Password is required"),
  timezone: z.string().optional(), // User's timezone offset in hours (e.g., "0" for UTC, "-5" for EST)
});

export type BlueskyConnectionData = z.infer<typeof blueskyConnectionSchema>;
