"use client";

import React from 'react';
import Link from 'next/link';
import { useUser } from '@/stores/hooks/useUser';
import { UserDropdown } from './UserDropdown';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

/**
 * Authentication navigation component
 * Shows login/signup buttons for unauthenticated users
 * Shows UserDropdown for authenticated users
 * Integrates with Legend State user store
 */
export const AuthNav: React.FC = () => {
  const { isAuthenticated, isLoading, isInitialized } = useUser();

  // Show loading state until auth is initialized
  if (!isInitialized || isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    );
  }

  // Show user dropdown if authenticated
  if (isAuthenticated) {
    return <UserDropdown />;
  }

  // Show login/signup buttons if not authenticated
  return (
    <div className="flex items-center space-x-2">
      <Button variant="ghost" asChild>
        <Link href="/signin">Sign In</Link>
      </Button>
      <Button asChild>
        <Link href="/signup">Get Started</Link>
      </Button>
    </div>
  );
};