import { z } from "zod";

// Team creation schema
export const createTeamSchema = z.object({
  name: z.string().min(3, "Team name must be at least 3 characters").max(255, "Team name must be less than 255 characters"),
  description: z.string().max(1000, "Description must be less than 1000 characters").optional(),
});

// Team update schema
export const updateTeamSchema = z.object({
  name: z.string().min(3, "Team name must be at least 3 characters").max(255, "Team name must be less than 255 characters").optional(),
  description: z.string().max(1000, "Description must be less than 1000 characters").optional(),
});

// Team invitation schema
export const inviteTeamMemberSchema = z.object({
  email: z.string().email("Invalid email address"),
  role: z.enum(["administrator", "user"], {
    message: "Role must be 'administrator' or 'user'"
  }),
});

// Team member role update schema
export const updateMemberRoleSchema = z.object({
  userId: z.string().uuid("Invalid user ID"),
  role: z.enum(["administrator", "user"], {
    message: "Role must be 'administrator' or 'user'"
  }),
});

// Team MP follow schema
export const teamMpFollowSchema = z.object({
  memberId: z.number().int().positive("Invalid MP ID"),
});

// Team notification preferences schema
export const teamNotificationPreferencesSchema = z.object({
  emailNotifications: z.boolean().optional(),
  inAppNotifications: z.boolean().optional(),
  mpActivityNotifications: z.boolean().optional(),
  clipProcessingNotifications: z.boolean().optional(),
  teamActivityNotifications: z.boolean().optional(),
});

// Accept invitation schema
export const acceptInvitationSchema = z.object({
  token: z.string().min(1, "Invitation token is required"),
});

// Transfer ownership schema
export const transferOwnershipSchema = z.object({
  newOwnerId: z.string().uuid("Invalid user ID"),
});

// Team context schema (for state management)
export const teamContextSchema = z.object({
  currentTeamId: z.string().uuid().nullable(),
  isPersonalMode: z.boolean(),
});

// Invitation action params schema (resend / cancel)
export const invitationActionSchema = z.object({
  teamId: z.string().uuid(),
  invitationId: z.string().uuid(),
});

// Member action params schema (update role / remove)
export const memberActionSchema = z.object({
  teamId: z.string().uuid(),
  userId: z.string().uuid(),
});

// Types derived from schemas
export type CreateTeamData = z.infer<typeof createTeamSchema>;
export type UpdateTeamData = z.infer<typeof updateTeamSchema>;
export type InviteTeamMemberData = z.infer<typeof inviteTeamMemberSchema>;
export type UpdateMemberRoleData = z.infer<typeof updateMemberRoleSchema>;
export type TeamMpFollowData = z.infer<typeof teamMpFollowSchema>;
export type TeamNotificationPreferencesData = z.infer<typeof teamNotificationPreferencesSchema>;
export type AcceptInvitationData = z.infer<typeof acceptInvitationSchema>;
export type TransferOwnershipData = z.infer<typeof transferOwnershipSchema>;
export type TeamContextData = z.infer<typeof teamContextSchema>;