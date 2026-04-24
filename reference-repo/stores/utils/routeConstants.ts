/**
 * Shared route constants used by both client-side (userStore) and
 * server-side (serverAuth) route protection logic.
 */

export const SETUP_ROUTES: string[] = ["/setup", "/mp-setup", "/team-setup"];

export const DYNAMIC_PROTECTED_ROUTES: string[] = ["/dashboard/"];

export const AUTH_ROUTES: string[] = ["/signin", "/signup", "/forgot-password"];

export const PUBLIC_ROUTES: string[] = [
  "/teams/invite",
  "/clips",
  "/embed",
  "/integrations/social",
];
