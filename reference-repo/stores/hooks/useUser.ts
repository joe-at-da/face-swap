"use client";

import { useSelector } from '@legendapp/state/react';
import { userStore$, authActions, uiActions, routeProtection } from '../userStore';

/**
 * Hook to access current user state
 * Uses useSelector to get reactive values from observables (Legend State v3 beta)
 */
export const useUser = () => {
  const user = useSelector(() => userStore$.user.get());
  const isAuthenticated = useSelector(() => userStore$.isAuthenticated.get());
  const isLoading = useSelector(() => userStore$.isLoading.get());
  const isInitialized = useSelector(() => userStore$.isInitialized.get());
  const profile = useSelector(() => userStore$.profile.get());
  const isParliamentMember = useSelector(() => userStore$.isParliamentMember.get());
  const isFirstLogin = useSelector(() => userStore$.isFirstLogin.get());
  const error = useSelector(() => userStore$.error.get());

  return {
    user,
    isAuthenticated,
    isLoading,
    isInitialized,
    profile,
    isParliamentMember,
    isFirstLogin,
    error,
  };
};

/**
 * Hook to access authentication actions
 */
export const useAuth = () => {
  const isLoading = useSelector(() => userStore$.isLoading.get());
  const error = useSelector(() => userStore$.error.get());

  return {
    ...authActions,
    isLoading,
    error,
  };
};

/**
 * Hook to access user dropdown UI state
 */
export const useUserDropdown = () => {
  const isDropdownOpen = useSelector(() => userStore$.showUserDropdown.get());
  const { showDropdown, ...otherActions } = uiActions;

  return {
    showUserDropdown: isDropdownOpen,
    showDropdown,
    ...otherActions,
  };
};

/**
 * Hook to access route protection utilities
 */
export const useRouteProtection = () => {
  return routeProtection;
};

/**
 * Hook to access session state
 */
export const useSession = () => {
  const session = useSelector(() => userStore$.session.get());
  const isSessionExpired = useSelector(() => userStore$.isSessionExpired.get());

  return {
    session,
    isSessionExpired,
    refreshSession: authActions.refreshSession,
  };
};

/**
 * Combined hook for full user store access
 */
export const useUserStore = () => {
  const user = useUser();
  const auth = useAuth();
  const ui = useUserDropdown();
  const routing = useRouteProtection();
  const session = useSession();

  return {
    ...user,
    ...auth,
    ...ui,
    ...routing,
    ...session,
  };
};