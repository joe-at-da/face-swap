"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SmartAvatar } from "@/components/smart-avatar";
import { Settings, LogOut, Crown, LayoutDashboard, ChevronDown, User } from "lucide-react";
import Link from "next/link";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { isMPEmail } from "@/lib/domains";

interface UserDropdownProps {
  user: SupabaseUser;
  variant?: "homepage" | "dashboard";
}

export function UserDropdown({ user, variant = "dashboard" }: UserDropdownProps) {
  const router = useRouter();
  const supabase = createSupabaseBrowserClient();

  const handleSignOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        toast.error("Failed to sign out");
        return;
      }

      router.push("/");
      router.refresh();
    } catch {
      toast.error("Failed to sign out");
    }
  };

  const isMP = isMPEmail(user.email);
  const firstName = user.user_metadata?.first_name || "";
  const lastName = user.user_metadata?.last_name || "";
  const profileImage = user.user_metadata?.profile_image;
  const displayName = firstName && lastName ? `${firstName} ${lastName}` : user.email?.split('@')[0];

  const isOnDashboard = variant === "dashboard";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {isOnDashboard ? (
          <Button variant="ghost" className="relative h-10 w-10 rounded-full">
            <SmartAvatar
              profileImage={profileImage}
              firstName={firstName}
              lastName={lastName}
              email={user.email}
              isMP={isMP}
              className="h-8 w-8"
              enableLazyLoading={false}
            />
          </Button>
        ) : (
          <Button
            variant="ghost"
            className="flex items-center gap-2 px-3 justify-start"
          >
            <User className="h-4 w-4" />
            <span className="hidden md:block max-w-[200px] truncate text-sm">
              {user.email}
            </span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">
              {displayName}
            </p>
            <div className="flex items-center space-x-2">
              <p className="text-xs leading-none text-muted-foreground truncate">
                {user.email}
              </p>
              {isMP && <Crown className="h-3 w-3 text-primary" />}
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Show Dashboard link only on homepage */}
        {!isOnDashboard && (
          <>
            <DropdownMenuItem asChild>
              <Link href="/dashboard" className="cursor-pointer">
                <LayoutDashboard className="mr-2 h-4 w-4" />
                <span>Dashboard</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}

        {/* Show Settings link only on dashboard */}
        {isOnDashboard && (
          <>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings" className="cursor-pointer">
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}

        <DropdownMenuItem
          onClick={handleSignOut}
          className="cursor-pointer"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Sign out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}