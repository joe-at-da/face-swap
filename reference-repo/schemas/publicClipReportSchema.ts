import { z } from "zod";

export const publicClipReportReasonOptions = [
  "wrong_clip",
  "misleading",
  "copyright_or_privacy",
  "harmful_or_abusive",
  "other",
] as const;

export const publicClipReportSchema = z.object({
  clipId: z.string().trim().uuid("Invalid clip reference"),
  reason: z.enum(publicClipReportReasonOptions, {
    error: "Please select a reason for this report",
  }),
  details: z
    .string()
    .trim()
    .max(2000, "Details must be under 2000 characters")
    .optional()
    .or(z.literal(""))
    .transform((value) => value || undefined),
});

/** Form-only schema (excludes clipId which comes from component props) */
export const publicClipReportFormSchema = publicClipReportSchema.omit({ clipId: true });

export type PublicClipReportFormValues = z.input<typeof publicClipReportFormSchema>;

export type PublicClipReportInput = z.input<typeof publicClipReportSchema>;
export type PublicClipReportData = z.output<typeof publicClipReportSchema>;
export type PublicClipReportReason = PublicClipReportData["reason"];
export type PublicClipReportFieldErrors = z.inferFlattenedErrors<
  typeof publicClipReportSchema
>["fieldErrors"];
