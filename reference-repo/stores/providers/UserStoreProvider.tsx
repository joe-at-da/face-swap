"use client";

import React, { useEffect, type ReactNode } from 'react';
import { initializeAuthSubscription, cleanupAuthSubscription, waitForAuth } from '../userStore';

interface UserStoreProviderProps {
  children: ReactNode;
}

/**
 * Provider component that initializes the user store and auth subscription
 * Should be placed high in the component tree, typically in the root layout
 */
export const UserStoreProvider: React.FC<UserStoreProviderProps> = ({ children }) => {
  useEffect(() => {
    // Initialize auth subscription when component mounts
    initializeAuthSubscription();

    // Cleanup subscription when component unmounts
    return () => {
      cleanupAuthSubscription();
    };
  }, []);

  return <>{children}</>;
};

/**
 * Hook to wait for auth initialization before rendering
 * Useful for components that need to ensure auth state is loaded
 */
export const useWaitForAuth = () => {
  const [isReady, setIsReady] = React.useState(false);

  useEffect(() => {
    let mounted = true;
    
    waitForAuth().then(() => {
      if (mounted) {
        setIsReady(true);
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  return isReady;
};

/**
 * Component that shows loading state until auth is initialized
 */
interface AuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ 
  children, 
  fallback = <div>Loading...</div> 
}) => {
  const isReady = useWaitForAuth();

  if (!isReady) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};