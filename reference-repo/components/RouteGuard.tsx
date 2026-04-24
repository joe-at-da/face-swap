"use client";

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useUser, useRouteProtection } from '@/stores/hooks/useUser';
import { Loader2 } from 'lucide-react';

interface RouteGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

/**
 * Client-side route guard component
 * Protects routes based on authentication state and user permissions
 * Integrates with Legend State user store
 */
export const RouteGuard: React.FC<RouteGuardProps> = ({ 
  children, 
  fallback = (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-2">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">Checking permissions...</p>
      </div>
    </div>
  ),
  redirectTo 
}) => {
  const router = useRouter();
  const pathname = usePathname();
  const { isInitialized, isLoading } = useUser();
  const { canAccessRoute, getRedirectUrl } = useRouteProtection();

  useEffect(() => {
    // Only check routes after auth is initialized
    if (!isInitialized || isLoading) {
      return;
    }

    const hasAccess = canAccessRoute(pathname);
    
    if (!hasAccess) {
      const defaultRedirect = getRedirectUrl(pathname);
      const targetRoute = redirectTo || defaultRedirect || '/';
      
      console.log(`RouteGuard: Redirecting from ${pathname} to ${targetRoute}`);
      router.replace(targetRoute);
    }
  }, [isInitialized, isLoading, pathname, canAccessRoute, getRedirectUrl, router, redirectTo]);

  // Show loading while auth initializes
  if (!isInitialized || isLoading) {
    return <>{fallback}</>;
  }

  // Check if user can access current route
  const hasAccess = canAccessRoute(pathname);
  
  if (!hasAccess) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * Higher-order component for route protection
 */
export const withRouteGuard = <P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    fallback?: React.ReactNode;
    redirectTo?: string;
  }
) => {
  return function ProtectedComponent(props: P) {
    return (
      <RouteGuard fallback={options?.fallback} redirectTo={options?.redirectTo}>
        <Component {...props} />
      </RouteGuard>
    );
  };
};