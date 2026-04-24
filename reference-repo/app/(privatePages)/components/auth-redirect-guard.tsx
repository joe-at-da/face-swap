"use client";

import { useEffect } from "react";
import { useUser } from "@/stores/hooks/useUser";

interface AuthRedirectGuardProps {
  children: React.ReactNode;
}

/**
 * Client component that redirects to home when user logs out (including from other tabs)
 * This complements the server-side auth check in the layout
 */
export function AuthRedirectGuard({ children }: AuthRedirectGuardProps) {
  const { isAuthenticated, isInitialized } = useUser();

  // Redirect to home if user becomes unauthenticated (e.g., logout from another tab)
  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      // Use window.location for reliable redirect (avoids conflicts with server action redirects)
      window.location.href = '/';
    }
  }, [isInitialized, isAuthenticated]);

  // If user is logged out, show a message while redirecting
  if (isInitialized && !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Redirecting to home...</div>
      </div>
    );
  }

  return <>{children}</>;
}
