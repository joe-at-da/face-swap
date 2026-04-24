import { z } from "zod";

export const productInterestOptions = [
  "Parliamentary Communications",
  "Parliamentary Monitoring",
] as const;

export const contactSchema = z.object({
  contactName: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(200, "Name must be under 200 characters"),
  contactEmail: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, "Email is required")
    .email("Please enter a valid email address")
    .max(254, "Email must be under 254 characters"),
  phoneNumber: z
    .string()
    .max(20, "Phone number must be under 20 characters")
    .regex(/^[0-9+\-() ]*$/, "Please enter a valid phone number")
    .optional()
    .or(z.literal("")),
  productInterest: z.array(z.enum(productInterestOptions)).default([]),
  message: z
    .string()
    .trim()
    .min(1, "Message is required")
    .max(5000, "Message must be under 5000 characters"),
});

export type ContactFormData = z.input<typeof contactSchema>;
