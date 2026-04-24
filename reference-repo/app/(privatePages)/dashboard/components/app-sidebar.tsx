"use client";

import * as React from "react";
import {
  LayoutDashboard,
  Plus,
  Video,
  MonitorPlay,
  Settings,
  LogOut,
  Users,
  User as UserIcon,
  ChevronDown,
  AlertCircle,
  FileText,
  Film,
  Library,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import {
  useTeamActions,
  useIsPersonalMode,
  useCurrentTeam,
  useUserTeams,
  useCurrentTeamId,
  type TeamWithRole,
} from "@/stores/teamStore";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SmartAvatar } from "@/components/smart-avatar";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { toast } from "sonner";
import Image from "next/image";

// Navigation items generator based on user type and mode
const getPersonalNavItems = (
  isMP: boolean,
  isAdmin: boolean,
  canAccessAnalytics: boolean,
  isLiberalDemocrat: boolean
) => {
  const items = [
    {
      title: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
  ];

  if (isAdmin) {
    items.push({
      title: "All MPs Clips",
      href: "/dashboard/all-clips",
      icon: Film,
    });
  }

  // Only MPs can see Speech Library
  if (isMP) {
    items.push({
      title: "Speech Library",
      href: "/dashboard/create-clips",
      icon: Library,
    });
  }

  if (isLiberalDemocrat) {
    items.push({
      title: "All LD Clips",
      href: "/dashboard/ld-clips",
      icon: Film,
    });
  }

  items.push({
    title: "My Clips",
    href: "/dashboard/my-clips",
    icon: MonitorPlay,
  });

  if (canAccessAnalytics) {
    items.push({
      title: "Analytics",
      href: "/dashboard/analytics",
      icon: TrendingUp,
    });
  }

  items.push({
    title: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
  });

  return items;
};

const getTeamNavItems = (teamId: string, userRole: string, _isMP: boolean, isLiberalDemocrat: boolean) => {
  const items = [
    {
      title: "Dashboard",
      href: `/dashboard/teams/${teamId}`,
      icon: LayoutDashboard,
    },
  ];

  // All team members can access Speech Library (clips come from team owner's MP)
  items.push({
    title: "Speech Library",
    href: `/dashboard/create-clips?teamId=${teamId}`,
    icon: Library,
  });

  if (isLiberalDemocrat) {
    items.push({
      title: "All LD Clips",
      href: `/dashboard/ld-clips?teamId=${teamId}`,
      icon: Film,
    });
  }

  items.push({
    title: "Team Clips",
    href: `/dashboard/teams/${teamId}/clips`,
    icon: Video,
  });

  // All team members can see Team Members
  items.push({
    title: "Team Members",
    href: `/dashboard/teams/${teamId}/members`,
    icon: Users,
  });

  // Only owners and administrators can see Team Settings
  if (userRole === "owner" || userRole === "administrator") {
    items.push({
      title: "Team Settings",
      href: `/dashboard/teams/${teamId}/settings`,
      icon: Settings,
    });
  }

  items.push({
    title: "My Settings",
    href: "/dashboard/settings",
    icon: Settings,
  });

  return items;
};

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  user: User;
  canCreateTeam: boolean;
  canAccessAnalytics: boolean;
  isMP: boolean;
  isAdmin: boolean;
  isLiberalDemocrat: boolean;
  /** Team IDs whose owner is a Liberal Democrat MP */
  ldTeamIds: string[];
}

export function AppSidebar({
  user,
  canCreateTeam,
  canAccessAnalytics,
  isMP,
  isAdmin,
  isLiberalDemocrat,
  ldTeamIds,
  ...props
}: AppSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createSupabaseBrowserClient();

  // Team store state
  const isPersonalMode = useIsPersonalMode();
  const currentTeam = useCurrentTeam();
  const userTeams = useUserTeams();
  const currentTeamId = useCurrentTeamId();
  const teamActions = useTeamActions();

  // Track if client has mounted (to avoid hydration mismatch)
  const [isMounted, setIsMounted] = React.useState(false);

  // Use server-computed isMP for accurate MP detection
  const isUserTeamOnlyMember = user.user_metadata?.is_team_member === true && !isMP;

  // Load teams and handle client mounting
  React.useEffect(() => {
    setIsMounted(true);
    teamActions.loadUserTeams();

    // For team-only members, automatically switch to team mode if in personal mode
    if (isUserTeamOnlyMember && isPersonalMode && userTeams.length > 0) {
      const firstTeam = userTeams[0];
      teamActions.switchToTeam(firstTeam.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - run only on mount

  // Check if teams are loaded for team-only members
  React.useEffect(() => {
    if (
      isUserTeamOnlyMember &&
      isMounted &&
      userTeams.length > 0 &&
      isPersonalMode
    ) {
      const firstTeam = userTeams[0];
      teamActions.switchToTeam(firstTeam.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userTeams, isMounted]);

  // Show team nav when in team mode with a valid team
  // Only show after mount to avoid hydration mismatch
  const shouldShowTeamNav = isMounted && !isPersonalMode && currentTeamId;

  // Determine if personal navigation should be shown
  // Personal nav is shown ONLY when in personal mode
  // MPs can switch between personal and team mode
  // Regular users only see personal mode
  // Team-only members never see personal nav - they only see team nav
  // Only show after mount to avoid hydration mismatch
  const shouldShowPersonalNav =
    isMounted && isPersonalMode && !isUserTeamOnlyMember;

  const handleSignOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        toast.error("Failed to sign out");
        return;
      }

      teamActions.reset();
      router.push("/");
      router.refresh();
    } catch {
      toast.error("Failed to sign out");
    }
  };

  const firstName = user.user_metadata?.first_name || "";
  const lastName = user.user_metadata?.last_name || "";
  const profileImage = user.user_metadata?.profile_image;

  // Handle team switching with navigation
  const handleTeamSwitch = (teamId: string) => {
    // Switch to the team in the store
    teamActions.switchToTeam(teamId);

    // If we're currently on a team-specific page, navigate to the new team's equivalent page
    if (pathname.includes("/dashboard/teams/")) {
      // Extract the page type from the current path
      const pathParts = pathname.split("/");
      const currentTeamIndex = pathParts.indexOf("teams") + 1;

      if (pathParts[currentTeamIndex]) {
        // Get everything after the team ID
        const pageType = pathParts.slice(currentTeamIndex + 1).join("/");

        if (pageType) {
          // Navigate to the same page type for the new team (e.g., /members or /settings)
          router.push(`/dashboard/teams/${teamId}/${pageType}`);
        } else {
          // Just the team dashboard
          router.push(`/dashboard/teams/${teamId}`);
        }
      }
    } else {
      // If we're on a non-team page (e.g., /dashboard), navigate to the team dashboard
      router.push(`/dashboard/teams/${teamId}`);
    }
  };

  // Handle switching to personal mode
  const handlePersonalSwitch = () => {
    teamActions.switchToPersonal();

    // If we're on a team page, go back to main dashboard
    if (pathname.includes("/dashboard/teams/")) {
      router.push("/dashboard");
    }
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <div className="w-full px-2 py-3">
              {/* Expanded state - logo on left, trigger on right */}
              <div className="flex items-center justify-between w-full group-data-[state=collapsed]:hidden">
                <Link href="/dashboard" className="flex items-center">
                  <Image
                    src="/parlament-connect-logo.svg"
                    alt="Parliament Connect"
                    width={185}
                    height={64}
                    className="w-full h-auto max-w-[185px]"
                    priority
                  />
                </Link>
                <SidebarTrigger className="hidden md:block" />
              </div>

              {/* Collapsed state - logo on top, trigger below */}
              <div className="hidden group-data-[state=collapsed]:flex flex-col items-center justify-center w-full gap-2">
                <Link href="/dashboard" className="flex items-center justify-center">
                  <Image
                    src="/parliament-connect-logo-trigger.png"
                    alt="Parliament Connect"
                    width={30}
                    height={40}
                    className="w-[30px] h-[40px] object-cover"
                    priority
                  />
                </Link>
                <SidebarTrigger className="size-8" />
              </div>
            </div>
          </SidebarMenuItem>
        </SidebarMenu>

        {/* Team Context Switcher */}
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" className="w-full">
                  <div className="flex aspect-square size-8 items-center justify-center">
                    {isMounted && isPersonalMode ? (
                      <UserIcon className="size-4" />
                    ) : (
                      <Users className="size-4" />
                    )}
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">
                      {isMounted && isPersonalMode
                        ? "Personal"
                        : currentTeam?.name || "Team"}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">
                      {isMounted && isPersonalMode
                        ? "Personal workspace"
                        : currentTeam?.userRole || "Loading..."}
                    </span>
                  </div>
                  <ChevronDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg">
                {/* Personal Option - Only show for MPs and regular users, not team-only members */}
                {!isUserTeamOnlyMember && (
                  <>
                    <DropdownMenuItem
                      onClick={handlePersonalSwitch}
                      className="cursor-pointer"
                    >
                      <UserIcon className="mr-2 h-4 w-4" />
                      <div className="flex-1">
                        <div className="font-medium">Personal</div>
                        <div className="text-xs text-muted-foreground">
                          Personal workspace
                        </div>
                      </div>
                      {isPersonalMode && (
                        <div className="ml-auto text-primary">✓</div>
                      )}
                    </DropdownMenuItem>
                    {userTeams.length > 0 && <DropdownMenuSeparator />}
                  </>
                )}

                {/* Teams Section */}
                {userTeams.length > 0 && (
                  <>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                      Teams
                    </div>
                    {userTeams.map((team: TeamWithRole) => (
                      <DropdownMenuItem
                        key={team.id}
                        onClick={() => handleTeamSwitch(team.id)}
                        className="cursor-pointer"
                      >
                        <Users className="mr-2 h-4 w-4" />
                        <div className="flex-1">
                          <div className="font-medium">{team.name}</div>
                          <div className="text-xs text-muted-foreground capitalize">
                            {team.userRole}
                          </div>
                        </div>
                        {currentTeam?.id === team.id && (
                          <div className="ml-auto text-primary">✓</div>
                        )}
                      </DropdownMenuItem>
                    ))}
                  </>
                )}

                {/* Show Create Team or Contact Us message */}
                <DropdownMenuSeparator />
                {canCreateTeam ? (
                  <DropdownMenuItem asChild>
                    <Link
                      href="/dashboard/teams/new"
                      className="cursor-pointer"
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Create Team
                    </Link>
                  </DropdownMenuItem>
                ) : (
                  <>
                    <DropdownMenuItem disabled>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Team
                    </DropdownMenuItem>
                    <div className="px-2 py-1.5">
                      <div className="flex items-start gap-2 text-xs text-muted-foreground">
                        <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="leading-relaxed">
                            Contact us to create a team
                          </p>
                          <Link
                            href="/contact"
                            className="text-primary hover:underline mt-1 inline-block font-medium"
                          >
                            Contact Us
                          </Link>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Personal Navigation - Show conditionally based on user type and mode */}
        {shouldShowPersonalNav && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {getPersonalNavItems(isMP, isAdmin, canAccessAnalytics, isLiberalDemocrat).map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton
                        asChild
                        tooltip={item.title}
                        isActive={isActive}
                        className="p-4"
                      >
                        <Link href={item.href}>
                          <item.icon />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Team Navigation - Show when in team mode */}
        {(shouldShowTeamNav || (isUserTeamOnlyMember && isMounted)) &&
          currentTeamId && (
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {getTeamNavItems(
                    currentTeamId,
                    currentTeam?.userRole || "user",
                    isMP,
                    ldTeamIds.includes(currentTeamId),
                  ).map((item) => {
                    const isActive =
                      pathname === item.href ||
                      pathname.startsWith(item.href + "/");
                    return (
                      <SidebarMenuItem key={item.title}>
                        <SidebarMenuButton
                          asChild
                          tooltip={item.title}
                          isActive={isActive}
                          className="p-4"
                        >
                          <Link href={item.href}>
                            <item.icon />
                            <span>{item.title}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )}

        {/* Summaries Dropdown - Hidden on production */}
        {process.env.NEXT_PUBLIC_FRONTEND_URL !==
          "https://parliamentconnect.com" && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <SidebarMenuButton tooltip="Summaries" className="p-4">
                        <FileText />
                        <span>Summaries</span>
                        <ChevronDown className="ml-auto size-4" />
                      </SidebarMenuButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg">
                      <DropdownMenuItem asChild>
                        <Link
                          href="/dashboard/summaries/prime-ministers-questions"
                          className="cursor-pointer"
                        >
                          PMQs
                        </Link>
                      </DropdownMenuItem>

                      <DropdownMenuItem asChild>
                        <Link
                          href="/dashboard/summaries/liberal-democrats"
                          className="cursor-pointer"
                        >
                          Liberal Democrat
                        </Link>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <SmartAvatar
                    profileImage={profileImage}
                    firstName={firstName}
                    lastName={lastName}
                    email={user.email}
                    isMP={isMP}
                    className="h-8 w-8 rounded-lg"
                    enableLazyLoading={false}
                  />
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate text-xs">{user.email}</span>
                  </div>
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="bottom"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuItem asChild>
                  <Link href="/dashboard/settings" className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleSignOut}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
