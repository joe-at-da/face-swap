import { z } from "zod";

// Profile Settings Schema
export const profileSettingsSchema = z.object({
  firstName: z
    .string()
    .min(1, "First name is required")
    .max(50, "First name must be less than 50 characters"),
  lastName: z
    .string()
    .min(1, "Last name is required")
    .max(50, "Last name must be less than 50 characters"),
  profileImage: z.string().optional().nullable(),
});

// Notification Settings Schema - all fields required with boolean values
export const notificationSettingsSchema = z.object({
  clipProcessingComplete: z.boolean(),
  weeklyPerformanceReport: z.boolean(),
  socialMediaShares: z.boolean(),
  systemUpdates: z.boolean(),
});

// Social Media Settings Schema
export const socialMediaSettingsSchema = z.object({
  twitter: z.boolean().default(false),
  facebook: z.boolean().default(false),
  tiktok: z.boolean().default(false),
  instagram: z.boolean().default(false),
});

// Danger Zone Schema
export const dangerZoneSchema = z.object({
  confirmationText: z
    .string()
    .min(1, "Please type DELETE to confirm")
    .refine((val) => val === "DELETE", {
      message: 'You must type "DELETE" to confirm account deletion',
    }),
});

// Type exports
export type ProfileSettingsData = z.infer<typeof profileSettingsSchema>;
export type NotificationSettingsData = z.infer<
  typeof notificationSettingsSchema
>;
export type SocialMediaSettingsData = z.infer<typeof socialMediaSettingsSchema>;
export type DangerZoneData = z.infer<typeof dangerZoneSchema>;
