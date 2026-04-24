import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import { UserDropdown } from "@/components/user-dropdown";
import { Logo } from "@/components/logo";
import type { User } from "@supabase/supabase-js";

interface DashboardHeaderProps {
  user: User;
}

export function DashboardHeader({ user }: DashboardHeaderProps) {
  return (
    <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 md:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center space-x-4">
            <Logo />
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="icon">
              <Bell className="h-5 w-5" />
            </Button>
            <UserDropdown user={user} variant="dashboard" />
          </div>
        </div>
      </div>
    </header>
  );
}
