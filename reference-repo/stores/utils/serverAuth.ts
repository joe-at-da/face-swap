import "server-only";

import type { User } from "@supabase/supabase-js";
import {
  SETUP_ROUTES,
  DYNAMIC_PROTECTED_ROUTES,
  AUTH_ROUTES,
  PUBLIC_ROUTES,
} from "@/stores/utils/routeConstants";

/**
 * Server-side route protection utilities
 * These mirror the client-side logic but work with server data
 */

export interface ServerRouteProtection {
  canAccessRoute: (pathname: string, user: User | null) => boolean;
  getRedirectUrl: (pathname: string, user: User | null) => string | null;
  isProtectedRoute: (pathname: string) => boolean;
  isAuthRoute: (pathname: string) => boolean;
}

const PROTECTED_ROUTES = [
  "/dashboard",
  ...SETUP_ROUTES,
  "/no-team-access",
];

export const serverRouteProtection: ServerRouteProtection = {
  canAccessRoute: (pathname: string, user: User | null) => {
    const isAuthenticated = !!user;
    const isFirstLogin = user?.user_metadata?.is_first_login ?? false;
    const isTeamMember =
      user?.user_metadata?.is_team_member ||
      user?.user_metadata?.invitation_token;

    // Allow public routes without authentication
    const isPublicRoute = PUBLIC_ROUTES.some((route) =>
      pathname.startsWith(route)
    );
    if (isPublicRoute) {
      return true;
    }

    const isProtected =
      PROTECTED_ROUTES.includes(pathname) ||
      DYNAMIC_PROTECTED_ROUTES.some((route) => pathname.startsWith(route));
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
      const isParliamentEmail = user?.user_metadata?.is_parliament_member === true;

      // Allow access to home page for first-login users
      if (pathname === "/") {
        return true;
      }

      // Block access to other routes except setup pages and no-team-access
      if (
        pathname !== "/setup" &&
        pathname !== "/mp-setup" &&
        pathname !== "/team-setup" &&
        pathname !== "/no-team-access"
      ) {
        return false;
      }

      // Team members should go to team-setup (check FIRST — takes priority)
      if (isTeamMember && (pathname === "/setup" || pathname === "/mp-setup")) {
        return false;
      }

      // Parliament users (non-team) should go to mp-setup
      if (
        isParliamentEmail &&
        !isTeamMember &&
        (pathname === "/setup" || pathname === "/team-setup")
      ) {
        return false;
      }

      // Regular users (non-parliament, non-team) should go to setup
      if (
        !isParliamentEmail &&
        !isTeamMember &&
        (pathname === "/mp-setup" || pathname === "/team-setup")
      ) {
        return false;
      }
    }

    // Users who completed setup shouldn't access setup pages
    if (
      (pathname === "/setup" ||
        pathname === "/mp-setup" ||
        pathname === "/team-setup") &&
      !isFirstLogin &&
      isAuthenticated
    ) {
      return false;
    }

    // Allow authenticated users to access no-team-access page
    if (pathname === "/no-team-access" && isAuthenticated) {
      return true;
    }

    return true;
  },

  getRedirectUrl: (pathname: string, user: User | null) => {
    const isAuthenticated = !!user;
    const isFirstLogin = user?.user_metadata?.is_first_login ?? false;
    const isTeamMember =
      user?.user_metadata?.is_team_member ||
      user?.user_metadata?.invitation_token;

    // Public routes don't need redirects
    const isPublicRoute = PUBLIC_ROUTES.some((route) =>
      pathname.startsWith(route)
    );
    if (isPublicRoute) {
      return null;
    }

    const isProtected =
      PROTECTED_ROUTES.includes(pathname) ||
      DYNAMIC_PROTECTED_ROUTES.some((route) => pathname.startsWith(route));
    const isAuthPage = AUTH_ROUTES.includes(pathname);

    // Protected routes without auth -> home
    if (isProtected && !isAuthenticated) {
      return "/";
    }

    // Auth pages with existing auth -> dashboard
    if (isAuthPage && isAuthenticated) {
      return "/dashboard";
    }

    // First login users need to go through setup
    if (isAuthenticated && isFirstLogin) {
      const isParliamentEmail = user?.user_metadata?.is_parliament_member === true;

      // Allow home page access, don't redirect
      if (pathname === "/") {
        return null;
      }

      // Redirect other routes (except setup pages and no-team-access) to appropriate setup
      if (
        pathname !== "/setup" &&
        pathname !== "/mp-setup" &&
        pathname !== "/team-setup" &&
        pathname !== "/no-team-access"
      ) {
        // Team members first (takes priority over parliament check)
        if (isTeamMember) {
          return "/team-setup";
        }
        if (isParliamentEmail) {
          return "/mp-setup";
        }
        return "/setup";
      }

      // Team members accessing wrong setup (check FIRST — takes priority)
      if (isTeamMember && (pathname === "/setup" || pathname === "/mp-setup")) {
        return "/team-setup";
      }

      // Parliament users (non-team) accessing wrong setup
      if (
        isParliamentEmail &&
        !isTeamMember &&
        (pathname === "/setup" || pathname === "/team-setup")
      ) {
        return "/mp-setup";
      }

      // Regular users accessing wrong setup
      if (
        !isParliamentEmail &&
        !isTeamMember &&
        (pathname === "/mp-setup" || pathname === "/team-setup")
      ) {
        return "/setup";
      }
    }

    // Completed users accessing setup pages
    if (
      (pathname === "/setup" ||
        pathname === "/mp-setup" ||
        pathname === "/team-setup") &&
      !isFirstLogin &&
      isAuthenticated
    ) {
      return "/dashboard";
    }

    return null;
  },

  isProtectedRoute: (pathname: string) => {
    return (
      PROTECTED_ROUTES.includes(pathname) ||
      DYNAMIC_PROTECTED_ROUTES.some((route) => pathname.startsWith(route))
    );
  },

  isAuthRoute: (pathname: string) => {
    return AUTH_ROUTES.includes(pathname);
  },
};

/**
 * Utility to check if user is a Parliament member / MP
 */
export const isParliamentMember = (user: User | null): boolean => {
  return user?.user_metadata?.is_parliament_member === true;
};

/**
 * Utility to check if user is on first login
 */
export const isFirstLoginCheck = (user: User | null): boolean => {
  return user?.user_metadata?.is_first_login ?? false;
};
