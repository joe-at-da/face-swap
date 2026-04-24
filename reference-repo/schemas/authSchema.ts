import { z } from "zod";

export const emailSchema = z.string().trim().toLowerCase().email();

// Sign-in form schema using only email (passwordless)
export const signInSchema = z.object({
  email: emailSchema,
});

// Extended sign-in schema with optional invitation fields
export const signInWithInviteSchema = signInSchema.extend({
  invitationToken: z.string().trim().min(1).max(255).optional(),
  acceptedTerms: z.boolean().optional(),
});

export const signupSchema = signInSchema.extend({
  acceptedTerms: z.boolean().refine((value) => value, {
    message: "You must agree to the Terms & Conditions",
  }),
  invitationToken: z.string().trim().min(1).max(255).optional(),
});

// OTP verification schema
export const otpVerificationSchema = z.object({
  email: emailSchema,
  token: z
    .string()
    .min(6, "OTP must be 6 digits")
    .max(6, "OTP must be 6 digits"),
});

// Account setup schemas
export const setupStep1Schema = z.object({
  firstName: z
    .string()
    .min(1, "First name is required")
    .max(50, "First name must be less than 50 characters")
    .trim(),
  lastName: z
    .string()
    .min(1, "Last name is required")
    .max(50, "Last name must be less than 50 characters")
    .trim(),
  profileImage: z
    .union([
      z.string().url().optional(), // URL string for uploaded images
      z.any().optional(), // File input for new uploads
    ])
    .optional()
    .refine((value) => {
      if (!value) return true; // Optional
      if (typeof value === "string") return true; // Already uploaded URL
      if (value.length === 0) return true; // No file selected
      const validTypes = ["image/jpeg", "image/png", "image/webp"];
      return validTypes.includes(value[0]?.type);
    }, "Please select a valid image file (JPEG, PNG, or WebP)")
    .refine((value) => {
      if (!value) return true; // Optional
      if (typeof value === "string") return true; // Already uploaded URL
      if (value.length === 0) return true; // No file selected
      return value[0]?.size <= 25 * 1024 * 1024; // 25MB limit
    }, "Image must be less than 25MB"),
});

export const setupStep2Schema = z.object({
  twitter: z.boolean(),
  facebook: z.boolean(),
  tiktok: z.boolean(),
  instagram: z.boolean(),
});

export const setupStep3Schema = z.object({
  selectedMpId: z
    .number()
    .min(1, "Please select an MP to follow")
    .int("Invalid MP selection"),
});

// Combined setup schema for final submission
export const accountSetupSchema = z.object({
  ...setupStep1Schema.shape,
  ...setupStep2Schema.shape,
  ...setupStep3Schema.shape,
});

// App review password login schema
export const appReviewPasswordSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Password is required"),
});

export type SignInFormData = z.infer<typeof signInSchema>;
export type SignInWithInviteData = z.infer<typeof signInWithInviteSchema>;
export type SignUpFormData = z.infer<typeof signupSchema>;
export type OtpVerificationData = z.infer<typeof otpVerificationSchema>;
export type AppReviewPasswordData = z.infer<typeof appReviewPasswordSchema>;
export type SetupStep1Data = z.infer<typeof setupStep1Schema>;
export type SetupStep2Data = z.infer<typeof setupStep2Schema>;
export type SetupStep3Data = z.infer<typeof setupStep3Schema>;
export type AccountSetupData = z.infer<typeof accountSetupSchema>;
