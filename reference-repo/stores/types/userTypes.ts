import type { User, Session } from '@supabase/supabase-js';

// Supabase User Profile type from generated types
// TODO: Create profiles table in database
// export type UserProfile = Database['public']['Tables']['profiles']['Row'];
export type UserProfile = {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
};

// Core user state interface
export interface UserState {
  // Auth State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean; // Track if auth has been initialized
  
  // Profile State
  profile: UserProfile | null;
  isParliamentMember: boolean;
  isFirstLogin: boolean;
  
  // UI State
  showUserDropdown: boolean;
  
  // Session Management
  session: Session | null;
  isSessionExpired: boolean;
  
  // Error State
  error: string | null;
}

// Auth action types
export interface AuthActions {
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateProfile: (updates: Partial<UserProfile>) => Promise<{ error?: string }>;
  completeSetup: () => Promise<{ error?: string }>;
  clearError: () => void;
}

// UI action types
export interface UIActions {
  toggleUserDropdown: () => void;
  hideUserDropdown: () => void;
  showDropdown: () => void;
}

// Route protection types
export interface RouteProtection {
  canAccessRoute: (pathname: string) => boolean;
  getRedirectUrl: (pathname: string) => string | null;
  isProtectedRoute: (pathname: string) => boolean;
  isAuthRoute: (pathname: string) => boolean;
}

// Combined store interface
export interface UserStore extends UserState, AuthActions, UIActions, RouteProtection {}

// Auth event types from Supabase
export type AuthEvent = 
  | 'INITIAL_SESSION'
  | 'SIGNED_IN' 
  | 'SIGNED_OUT'
  | 'TOKEN_REFRESHED'
  | 'USER_UPDATED'
  | 'PASSWORD_RECOVERY';

// Store configuration
export interface StoreConfig {
  persistKey: string;
  enablePersistence: boolean;
  enableDevTools: boolean;
}