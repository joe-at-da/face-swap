"use client";

import React from 'react';
import { useUser, useAuth, useUserDropdown } from '@/stores/hooks/useUser';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  User,
  Settings,
  LogOut,
  Shield,
  Loader2
} from 'lucide-react';
import { useRouter } from 'next/navigation';

/**
 * User dropdown component that integrates with the Legend State user store
 * Shows user info, authentication status, and provides auth actions
 */
export const UserDropdown: React.FC = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    isParliamentMember,
    isFirstLogin
  } = useUser();

  const { signOut } = useAuth();
  const { showUserDropdown, hideUserDropdown } = useUserDropdown();

  const router = useRouter();

  // Don't render anything if not authenticated
  if (!isAuthenticated || !user) {
    return null;
  }

  const handleSignOut = async () => {
    hideUserDropdown();
    await signOut();
    router.push('/');
  };

  const handleSettings = () => {
    hideUserDropdown();
    router.push('/settings');
  };

  const handleDashboard = () => {
    hideUserDropdown();
    router.push('/dashboard');
  };

  const getUserInitials = (email: string | undefined) => {
    if (!email) return 'U';
    const name = email.split('@')[0];
    return name
      .split('.')
      .map(part => part.charAt(0).toUpperCase())
      .join('')
      .slice(0, 2);
  };

  return (
    <DropdownMenu
      open={Boolean(showUserDropdown)}
      onOpenChange={(open) => {
        if (!open) {
          hideUserDropdown();
        }
      }}
    >
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="relative h-10 w-10 rounded-full p-0"
          disabled={Boolean(isLoading)}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Avatar className="h-10 w-10">
              <AvatarImage
                src={user?.user_metadata?.avatar_url}
                alt={user?.email || 'User'}
              />
              <AvatarFallback>
                {getUserInitials(user?.email)}
              </AvatarFallback>
            </Avatar>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-80" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-2">
            <div className="flex items-center space-x-2">
              <p className="text-sm font-medium leading-none">
                {user?.user_metadata?.full_name || user?.email?.split('@')[0]}
              </p>
              {isParliamentMember && (
                <Badge variant="secondary" className="text-xs">
                  <Shield className="mr-1 h-3 w-3" />
                  MP
                </Badge>
              )}
            </div>
            <p className="text-xs leading-none text-muted-foreground">
              {user?.email}
            </p>
            {isFirstLogin && (
              <Badge variant="outline" className="w-fit text-xs">
                Setup Required
              </Badge>
            )}
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={handleDashboard} className="cursor-pointer">
          <User className="mr-2 h-4 w-4" />
          <span>Dashboard</span>
        </DropdownMenuItem>

        <DropdownMenuItem onClick={handleSettings} className="cursor-pointer">
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={handleSignOut}
          className="cursor-pointer text-red-600 focus:text-red-600"
          disabled={Boolean(isLoading)}
        >
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <LogOut className="mr-2 h-4 w-4" />
          )}
          <span>Sign Out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};