"use client";

import { observable, when } from '@legendapp/state';
import { syncObservable } from '@legendapp/state/sync';
import { ObservablePersistLocalStorage } from '@legendapp/state/persist-plugins/local-storage';
import type { Session, AuthChangeEvent } from '@supabase/supabase-js';
import { createSupabaseBrowserClient } from '@/supabase/supabaseBrowserClient';
import type { UserState, UserProfile, AuthActions, UIActions, RouteProtection } from './types/userTypes';
import { ErrorLogger } from '@/lib/errorLogger';
import { SETUP_ROUTES, DYNAMIC_PROTECTED_ROUTES, AUTH_ROUTES, PUBLIC_ROUTES } from '@/stores/utils/routeConstants';

import posthog from 'posthog-js';

// Initial state
const initialState: UserState = {
  // Auth State
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isInitialized: false,
  
  // Profile State
  profile: null,
  isParliamentMember: false,
  isFirstLogin: false,
  
  // UI State
  showUserDropdown: false,
  
  // Session Management
  session: null,
  isSessionExpired: false,
  
  // Error State
  error: null,
};

// Create the observable store
export const userStore$ = observable<UserState>(initialState);

// Persist auth state to localStorage with cross-tab sync
syncObservable(userStore$, {
  persist: {
    name: 'user-auth-state',
    plugin: ObservablePersistLocalStorage,
    transform: {
      load: (value: unknown) => {
        const savedData = value as Record<string, unknown> || {};
        return {
          ...initialState,
          user: savedData.user || null,
          session: savedData.session || null,
          isAuthenticated: Boolean(savedData.isAuthenticated),
          profile: savedData.profile || null,
          isParliamentMember: Boolean(savedData.isParliamentMember),
          isFirstLogin: Boolean(savedData.isFirstLogin),
        };
      },
      save: (value: UserState) => ({
        user: value.user,
        session: value.session,
        isAuthenticated: value.isAuthenticated,
        profile: value.profile,
        isParliamentMember: value.isParliamentMember,
        isFirstLogin: value.isFirstLogin,
      }),
    },
  },
  // Cross-tab synchronization: Listen for localStorage changes from other tabs
  subscribe: ({ refresh }) => {
    if (typeof window === 'undefined') return;

    const handleStorageChange = async (event: StorageEvent) => {
      // Only handle changes to our auth state key from other tabs
      if (event.key === 'user-auth-state' && event.newValue !== event.oldValue) {
        // Refresh the observable from localStorage
        refresh();
        // Also refresh Supabase session to ensure auth state is in sync
        const supabase = createSupabaseBrowserClient();
        await supabase.auth.getSession();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  },
});

// Auth Actions
export const authActions: AuthActions = {
  signIn: async (email: string, password: string) => {
    const supabase = createSupabaseBrowserClient();
    userStore$.isLoading.set(true);
    userStore$.error.set(null);
    
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      
      if (error) {
        ErrorLogger.logAuthError(error, 'signIn', undefined, 'auth');
        userStore$.error.set(error.message);
        return { error: error.message };
      }
      
      // State will be updated by auth subscription
      return {};
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred during sign in';
      ErrorLogger.logAuthError(error, 'signIn', undefined, 'auth');
      userStore$.error.set(errorMessage);
      return { error: errorMessage };
    } finally {
      userStore$.isLoading.set(false);
    }
  },

  signOut: async () => {
    const supabase = createSupabaseBrowserClient();
    userStore$.isLoading.set(true);
    
    try {
      await supabase.auth.signOut();
      // State will be reset by auth subscription
    } catch (error) {
      ErrorLogger.logAuthError(error, 'signOut', userStore$.user.get()?.id, 'auth');
      console.error('Sign out error:', error);
    } finally {
      userStore$.isLoading.set(false);
    }
  },

  refreshSession: async () => {
    const supabase = createSupabaseBrowserClient();
    
    try {
      const { error } = await supabase.auth.refreshSession();
      
      if (error) {
        console.error('Session refresh error:', error);
        userStore$.isSessionExpired.set(true);
      }
      
      // State will be updated by auth subscription if successful
    } catch (error) {
      console.error('Session refresh error:', error);
      userStore$.isSessionExpired.set(true);
    }
  },

  updateProfile: async (updates: Partial<UserProfile>) => {
    const supabase = createSupabaseBrowserClient();
    userStore$.isLoading.set(true);
    userStore$.error.set(null);
    
    try {
      const { error } = await supabase.auth.updateUser({
        data: updates,
      });
      
      if (error) {
        userStore$.error.set(error.message);
        return { error: error.message };
      }
      
      // Update local profile state
      if (userStore$.profile.get()) {
        userStore$.profile.set({
          ...userStore$.profile.get()!,
          ...updates,
        });
      }
      
      return {};
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred updating profile';
      userStore$.error.set(errorMessage);
      return { error: errorMessage };
    } finally {
      userStore$.isLoading.set(false);
    }
  },

  completeSetup: async () => {
    const supabase = createSupabaseBrowserClient();
    
    try {
      const { error } = await supabase.auth.updateUser({
        data: { is_first_login: false },
      });
      
      if (error) {
        userStore$.error.set(error.message);
        return { error: error.message };
      }
      
      userStore$.isFirstLogin.set(false);
      return {};
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred completing setup';
      userStore$.error.set(errorMessage);
      return { error: errorMessage };
    }
  },

  clearError: () => {
    userStore$.error.set(null);
  },
};

// UI Actions
export const uiActions: UIActions = {
  toggleUserDropdown: () => {
    userStore$.showUserDropdown.set(!userStore$.showUserDropdown.get());
  },

  hideUserDropdown: () => {
    userStore$.showUserDropdown.set(false);
  },

  showDropdown: () => {
    userStore$.showUserDropdown.set(true);
  },
};

// Route Protection (client-side)
export const routeProtection: RouteProtection = {
  canAccessRoute: (pathname: string) => {
    const isAuthenticated = userStore$.isAuthenticated.get();
    const isFirstLogin = userStore$.isFirstLogin.get();
    
    const protectedRoutes = ['/dashboard', ...SETUP_ROUTES];
    const isProtected = protectedRoutes.includes(pathname) ||
                       DYNAMIC_PROTECTED_ROUTES.some(route => pathname.startsWith(route));
    const isAuthPage = AUTH_ROUTES.includes(pathname);

    // If it's a protected route and user is not authenticated
    if (isProtected && !isAuthenticated) {
      return false;
    }

    // If user is authenticated and trying to access auth pages
    if (isAuthPage && isAuthenticated) {
      return false;
    }

    // Handle first login redirects
    if (isAuthenticated && isFirstLogin) {
      const user = userStore$.user.get();
      const isMP = user?.user_metadata?.is_parliament_member === true;
      const isTeamMember = user?.user_metadata?.is_team_member === true || !!user?.user_metadata?.invitation_token;

      // Allow home page for first-login users
      if (pathname === '/') {
        return true;
      }

      // Allow public routes for first-login users (OAuth popups, clips, etc.)
      if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
        return true;
      }

      if (pathname !== '/setup' && pathname !== '/mp-setup' && pathname !== '/team-setup') {
        return false;
      }

      // Team members should go to team-setup (check FIRST — takes priority)
      if (isTeamMember && (pathname === '/setup' || pathname === '/mp-setup')) {
        return false;
      }

      // MP users should go to mp-setup (only if not a team member)
      if (isMP && !isTeamMember && (pathname === '/setup' || pathname === '/team-setup')) {
        return false;
      }

      // Regular users should not access mp-setup or team-setup
      if (!isMP && !isTeamMember && (pathname === '/mp-setup' || pathname === '/team-setup')) {
        return false;
      }
    }

    // Users who completed setup shouldn't access setup pages
    if (SETUP_ROUTES.includes(pathname) && !isFirstLogin && isAuthenticated) {
      return false;
    }
    
    return true;
  },

  getRedirectUrl: (pathname: string) => {
    const isAuthenticated = userStore$.isAuthenticated.get();
    const isFirstLogin = userStore$.isFirstLogin.get();
    const user = userStore$.user.get();
    
    const protectedRoutes = ['/dashboard', ...SETUP_ROUTES];
    const isProtected = protectedRoutes.includes(pathname) ||
                       DYNAMIC_PROTECTED_ROUTES.some(route => pathname.startsWith(route));
    const isAuthPage = AUTH_ROUTES.includes(pathname);

    // Protected routes without auth -> home
    if (isProtected && !isAuthenticated) {
      return '/';
    }

    // Auth pages with existing auth -> dashboard
    if (isAuthPage && isAuthenticated) {
      return '/dashboard';
    }

    // First login users need to go through setup
    if (isAuthenticated && isFirstLogin) {
      const isMP = user?.user_metadata?.is_parliament_member === true;
      const isTeamMember = user?.user_metadata?.is_team_member === true || !!user?.user_metadata?.invitation_token;

      // Allow home page for first-login users
      if (pathname === '/') {
        return null;
      }

      // Allow public routes for first-login users (OAuth popups, clips, etc.)
      if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
        return null;
      }

      if (pathname !== '/setup' && pathname !== '/mp-setup' && pathname !== '/team-setup') {
        // Team members first (takes priority over parliament check)
        if (isTeamMember) return '/team-setup';
        return isMP ? '/mp-setup' : '/setup';
      }

      // Team members accessing wrong setup (check FIRST — takes priority)
      if (isTeamMember && (pathname === '/setup' || pathname === '/mp-setup')) {
        return '/team-setup';
      }

      // MP users (non-team) accessing wrong setup
      if (isMP && !isTeamMember && (pathname === '/setup' || pathname === '/team-setup')) {
        return '/mp-setup';
      }

      // Regular users accessing MP setup or team setup
      if (!isMP && !isTeamMember && (pathname === '/mp-setup' || pathname === '/team-setup')) {
        return '/setup';
      }
    }

    // Completed users accessing setup pages
    if (SETUP_ROUTES.includes(pathname) && !isFirstLogin && isAuthenticated) {
      return '/dashboard';
    }

    return null;
  },

  isProtectedRoute: (pathname: string) => {
    const protectedRoutes = ['/dashboard', ...SETUP_ROUTES];
    return protectedRoutes.includes(pathname) ||
           DYNAMIC_PROTECTED_ROUTES.some(route => pathname.startsWith(route));
  },

  isAuthRoute: (pathname: string) => {
    return AUTH_ROUTES.includes(pathname);
  },
};

// Auth State Subscription Manager
let authSubscription: { data: { subscription: { unsubscribe: () => void } } } | null = null;

export const initializeAuthSubscription = () => {
  const supabase = createSupabaseBrowserClient();
  
  if (authSubscription) {
    return; // Already initialized
  }
  
  authSubscription = supabase.auth.onAuthStateChange(
    async (event: AuthChangeEvent, session: Session | null) => {
      console.log('Auth state change:', event, session?.user?.email);
      
      switch (event) {
        case 'INITIAL_SESSION':
        case 'SIGNED_IN':
        case 'TOKEN_REFRESHED':
          if (session?.user) {
            const isParliamentMember = session.user.user_metadata?.is_parliament_member === true;
            const isFirstLogin = session.user.user_metadata?.is_first_login ?? false;

            userStore$.user.set(session.user);
            userStore$.session.set(session);
            userStore$.isAuthenticated.set(true);
            userStore$.isParliamentMember.set(isParliamentMember);
            userStore$.isFirstLogin.set(isFirstLogin);
            userStore$.isSessionExpired.set(false);
            userStore$.error.set(null);

            // Identify user in PostHog for analytics
            posthog.identify(session.user.id, {
              email: session.user.email,
              user_id: session.user.id,
              is_parliament_member: isParliamentMember,
              is_first_login: isFirstLogin,
              created_at: session.user.created_at,
            });

            // Load user profile if needed
            // This could be expanded to fetch profile from profiles table
          } else {
            // Handle case where session exists but no user
            userStore$.user.set(null);
            userStore$.session.set(null);
            userStore$.isAuthenticated.set(false);
            userStore$.profile.set(null);
            userStore$.isParliamentMember.set(false);
            userStore$.isFirstLogin.set(false);
          }
          break;
          
        case 'SIGNED_OUT':
          // Reset all state
          userStore$.user.set(null);
          userStore$.session.set(null);
          userStore$.isAuthenticated.set(false);
          userStore$.profile.set(null);
          userStore$.isParliamentMember.set(false);
          userStore$.isFirstLogin.set(false);
          userStore$.showUserDropdown.set(false);
          userStore$.isSessionExpired.set(false);
          userStore$.error.set(null);

          // Reset PostHog session and anonymize user
          posthog.reset();
          break;
          
        case 'USER_UPDATED':
          if (session?.user) {
            userStore$.user.set(session.user);

            // Update derived state from metadata
            const isFirstLogin = session.user.user_metadata?.is_first_login ?? false;
            userStore$.isFirstLogin.set(isFirstLogin);

            // Update user properties in PostHog
            posthog.setPersonProperties({
              email: session.user.email,
              is_first_login: isFirstLogin,
              updated_at: new Date().toISOString(),
            });
          }
          break;
      }
      
      userStore$.isLoading.set(false);
      userStore$.isInitialized.set(true);
    }
  );
};

export const cleanupAuthSubscription = () => {
  if (authSubscription) {
    authSubscription.data.subscription.unsubscribe();
    authSubscription = null;
  }
};

// Initialize auth subscription immediately for hydration
if (typeof window !== 'undefined') {
  initializeAuthSubscription();
}

// Wait for store to be initialized before allowing route checks
export const waitForAuth = () => {
  return when(userStore$.isInitialized, () => true);
};