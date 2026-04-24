import type { Tables, Database } from "@/supabaseTypes";

/**
 * Team role enum from database
 */
export type TeamRole = Database["public"]["Enums"]["team_role"];

/**
 * Team from database
 */
export type TeamRow = Tables<"teams">;

/**
 * Simple team information
 */
export type Team = {
  id: string;
  name: string;
  description: string | null;
} | null;

/**
 * Team member with user details
 * Combines team_members table with user_roles information
 */
export interface TeamMember {
  id: string;
  userId: string;
  email: string;
  username: string | null;
  role: TeamRole;
  joinedAt: string;
  isOwner: boolean;
  status: "accepted";
}

/**
 * Pending team invitation
 * Represents an invitation that hasn't been accepted yet
 */
export interface PendingInvitation {
  id: string;
  email: string;
  role: Exclude<TeamRole, "owner">;
  invitedAt: string;
  expiresAt: string;
  invitedBy: string;
  status: "pending" | "expired";
}

/**
 * Combined team members data
 * Includes both accepted members and pending invitations
 */
export interface TeamMembersData {
  members: TeamMember[];
  invitations: PendingInvitation[];
  userRole: TeamRole | null;
}
