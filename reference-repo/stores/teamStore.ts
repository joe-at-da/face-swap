"use client";

import { observable } from "@legendapp/state";
import { use$ } from "@legendapp/state/react";
import { Database } from "@/supabaseTypes";

// Team type from database
type Team = Database["public"]["Tables"]["teams"]["Row"];
type TeamRole = Database["public"]["Enums"]["team_role"];

// Team with user's role information
export interface TeamWithRole extends Team {
  userRole: TeamRole;
  memberCount?: number;
}

// Team context state
interface TeamContextState {
  currentTeamId: string | null;
  isPersonalMode: boolean;
  currentTeam: TeamWithRole | null;
  userTeams: TeamWithRole[];
  isLoading: boolean;
  error: string | null;
}

// Team store actions
interface TeamStoreActions {
  setCurrentTeamId: (teamId: string | null) => void;
  setIsPersonalMode: (isPersonal: boolean) => void;
  setCurrentTeam: (team: TeamWithRole | null) => void;
  setUserTeams: (teams: TeamWithRole[]) => void;
  switchToTeam: (teamId: string) => void;
  switchToPersonal: () => void;
  loadUserTeams: () => Promise<void>;
  createTeam: (name: string, description?: string) => Promise<Team>;
  updateTeam: (teamId: string, updates: Partial<Team>) => Promise<void>;
  deleteTeam: (teamId: string) => Promise<void>;
  inviteMember: (teamId: string, email: string, role: TeamRole) => Promise<void>;
  removeMember: (teamId: string, userId: string) => Promise<void>;
  updateMemberRole: (teamId: string, userId: string, role: TeamRole) => Promise<void>;
  acceptInvitation: (token: string) => Promise<void>;
  transferOwnership: (teamId: string, newOwnerId: string) => Promise<void>;
  canUserPublish: () => boolean;
  canUserManageTeam: () => boolean;
  canUserManageMembers: () => boolean;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

// Function to get initial state from localStorage
const getInitialState = (): TeamContextState => {
  // Only read from localStorage on client side
  if (typeof window !== "undefined") {
    const savedTeamId = localStorage.getItem("currentTeamId");
    const savedIsPersonal = localStorage.getItem("isPersonalMode");

    // If there's a saved team ID, user was in team mode
    // Otherwise check the explicit isPersonalMode value
    const isPersonalMode = savedTeamId
      ? false
      : (savedIsPersonal === null ? true : savedIsPersonal !== "false");

    return {
      currentTeamId: savedTeamId || null,
      isPersonalMode,
      currentTeam: null,
      userTeams: [],
      isLoading: false,
      error: null,
    };
  }

  // Default state for SSR
  return {
    currentTeamId: null,
    isPersonalMode: true,
    currentTeam: null,
    userTeams: [],
    isLoading: false,
    error: null,
  };
};

// Initial state
const initialState: TeamContextState = getInitialState();

// Define the full store type
type TeamStore = TeamContextState & { actions: TeamStoreActions };

// Create the observable store - first without actions to avoid circular reference
export const teamStore = observable<TeamStore>({
  ...initialState,
  actions: {} as TeamStoreActions, // Placeholder, will be defined below
});

// Define actions separately to avoid circular reference issues
const actions: TeamStoreActions = {
  setCurrentTeamId: (teamId: string | null) => {
    teamStore.currentTeamId.set(teamId);
    // Save to localStorage for persistence
    if (typeof window !== "undefined") {
      if (teamId) {
        localStorage.setItem("currentTeamId", teamId);
      } else {
        localStorage.removeItem("currentTeamId");
      }
    }
  },

  setIsPersonalMode: (isPersonal: boolean) => {
    teamStore.isPersonalMode.set(isPersonal);
    if (typeof window !== "undefined") {
      localStorage.setItem("isPersonalMode", String(isPersonal));
    }
  },

  setCurrentTeam: (team: TeamWithRole | null) => {
    teamStore.currentTeam.set(team);
  },

  setUserTeams: (teams: TeamWithRole[]) => {
    teamStore.userTeams.set(teams);
  },

  switchToTeam: (teamId: string) => {
    const team = teamStore.userTeams.get().find((t: TeamWithRole) => t.id === teamId);
    if (team) {
      actions.setCurrentTeamId(teamId);
      actions.setCurrentTeam(team);
      actions.setIsPersonalMode(false);
    }
  },

  switchToPersonal: () => {
    actions.setCurrentTeamId(null);
    actions.setCurrentTeam(null);
    actions.setIsPersonalMode(true);
  },

  loadUserTeams: async () => {
    actions.setLoading(true);
    actions.setError(null);

      try {
        const response = await fetch("/api/teams/user-teams");
        if (!response.ok) {
          throw new Error("Failed to load teams");
        }

        const data = await response.json();
        actions.setUserTeams(data.teams);

        // Get current state - this was already initialized from localStorage
        const currentTeamId = teamStore.currentTeamId.get();
        const isPersonalMode = teamStore.isPersonalMode.get();

        // If we're already in team mode with a saved team ID, update the current team data
        if (!isPersonalMode && currentTeamId) {
          const team = data.teams.find((t: TeamWithRole) => t.id === currentTeamId);
          if (team) {
            // Just update the current team data without changing mode
            actions.setCurrentTeam(team);
          } else {
            // Team no longer exists, switch to personal
            actions.switchToPersonal();
          }
        } else if (isPersonalMode) {
          // Already in personal mode, no action needed
          // Just ensure current team is null
          actions.setCurrentTeam(null);
        }
      } catch (error) {
        actions.setError(error instanceof Error ? error.message : "Failed to load teams");
      } finally {
        actions.setLoading(false);
      }
  },

  createTeam: async (name: string, description?: string) => {
    actions.setLoading(true);
    actions.setError(null);

      try {
        const response = await fetch("/api/teams", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description }),
        });

        if (!response.ok) {
          throw new Error("Failed to create team");
        }

        const data = await response.json();

        // Add the new team to the list
        const newTeamWithRole: TeamWithRole = {
          ...data.team,
          userRole: "owner",
        };

        teamStore.userTeams.set([...teamStore.userTeams.get(), newTeamWithRole]);

        // Switch to the new team
        actions.switchToTeam(data.team.id);

        return data.team;
      } catch (error) {
        actions.setError(error instanceof Error ? error.message : "Failed to create team");
        throw error;
      } finally {
        actions.setLoading(false);
      }
  },

  updateTeam: async (teamId: string, updates: Partial<Team>) => {
    actions.setLoading(true);
    actions.setError(null);

      try {
        const response = await fetch(`/api/teams/${teamId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates),
        });

        if (!response.ok) {
          throw new Error("Failed to update team");
        }

        const data = await response.json();

        // Update the team in the list
        const teams = teamStore.userTeams.get();
        const updatedTeams = teams.map((t: TeamWithRole) =>
          t.id === teamId ? { ...t, ...data.team } : t
        );
        teamStore.userTeams.set(updatedTeams);

        // Update current team if it's the one being updated
        if (teamStore.currentTeamId.get() === teamId) {
          teamStore.currentTeam.set({ ...teamStore.currentTeam.get()!, ...data.team });
        }
      } catch (error) {
        actions.setError(error instanceof Error ? error.message : "Failed to update team");
        throw error;
      } finally {
        actions.setLoading(false);
      }
  },

  deleteTeam: async (teamId: string) => {
    actions.setLoading(true);
    actions.setError(null);

      try {
        const response = await fetch(`/api/teams/${teamId}`, {
          method: "DELETE",
        });

        if (!response.ok) {
          throw new Error("Failed to delete team");
        }

        // Remove the team from the list
        const teams = teamStore.userTeams.get();
        teamStore.userTeams.set(teams.filter((t: TeamWithRole) => t.id !== teamId));

        // Switch to personal mode if the deleted team was current
        if (teamStore.currentTeamId.get() === teamId) {
          actions.switchToPersonal();
        }
      } catch (error) {
        actions.setError(error instanceof Error ? error.message : "Failed to delete team");
        throw error;
      } finally {
        actions.setLoading(false);
      }
  },

  inviteMember: async (teamId: string, email: string, role: TeamRole) => {
      const response = await fetch(`/api/teams/${teamId}/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, role }),
      });

      if (!response.ok) {
        throw new Error("Failed to send invitation");
      }
  },

  removeMember: async (teamId: string, userId: string) => {
      const response = await fetch(`/api/teams/${teamId}/members/${userId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to remove member");
      }
  },

  updateMemberRole: async (teamId: string, userId: string, role: TeamRole) => {
      const response = await fetch(`/api/teams/${teamId}/members/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });

      if (!response.ok) {
        throw new Error("Failed to update member role");
      }
  },

  acceptInvitation: async (token: string) => {
      const response = await fetch("/api/teams/accept-invitation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        throw new Error("Failed to accept invitation");
      }

      // Reload teams after accepting invitation
      const data = await response.json();
      if (data.teamId) {
        // Reload user teams to include the new team
        window.location.reload();
      }
  },

  transferOwnership: async (teamId: string, newOwnerId: string) => {
      const response = await fetch(`/api/teams/${teamId}/transfer-ownership`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newOwnerId }),
      });

      if (!response.ok) {
        throw new Error("Failed to transfer ownership");
      }

      // Update the team role locally
      const teams = teamStore.userTeams.get();
      const updatedTeams = teams.map((t: TeamWithRole) =>
        t.id === teamId ? { ...t, userRole: "administrator" as TeamRole } : t
      );
      teamStore.userTeams.set(updatedTeams);
  },

  canUserPublish: () => {
    const currentTeam = teamStore.currentTeam.get();
    if (!currentTeam) return false;

    return currentTeam.userRole === "owner" || currentTeam.userRole === "administrator";
  },

  canUserManageTeam: () => {
    const currentTeam = teamStore.currentTeam.get();
    if (!currentTeam) return false;

    return currentTeam.userRole === "owner";
  },

  canUserManageMembers: () => {
    const currentTeam = teamStore.currentTeam.get();
    if (!currentTeam) return false;

    return currentTeam.userRole === "owner" || currentTeam.userRole === "administrator";
  },

  setLoading: (loading: boolean) => {
    teamStore.isLoading.set(loading);
  },

  setError: (error: string | null) => {
    teamStore.error.set(error);
  },

  reset: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("currentTeamId");
      localStorage.removeItem("isPersonalMode");
    }
    // Re-initialize with default state after clearing localStorage
    teamStore.set({ ...getInitialState(), actions });
  },
};

// Assign the actions to the store
teamStore.actions.set(actions);

// Helper hooks for use in components - using Legend State's use() for proper reactivity
export const useTeamStore = () => {
  return use$(teamStore);
};

export const useTeamActions = () => {
  // Actions don't need reactivity, they're just functions
  return teamStore.actions.get();
};

export const useCurrentTeam = () => {
  return use$(teamStore.currentTeam);
};

export const useIsPersonalMode = () => {
  return use$(teamStore.isPersonalMode);
};

export const useUserTeams = () => {
  return use$(teamStore.userTeams);
};

export const useCurrentTeamId = () => {
  return use$(teamStore.currentTeamId);
};
