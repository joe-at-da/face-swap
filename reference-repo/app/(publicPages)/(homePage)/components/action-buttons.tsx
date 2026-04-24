"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";
import { LogIn as LogInIcon } from "lucide-react";
import { UserDropdown } from "@/components/user-dropdown";
import type { User } from "@supabase/supabase-js";
import { useUser } from "@/stores/hooks/useUser";

interface ActionButtonsProps {
    isAuthenticated: boolean;
    user?: User | null;
    onLinkClick?: () => void;
}

export default function ActionButtons({ isAuthenticated: serverAuth, user: serverUser, onLinkClick }: ActionButtonsProps) {
    // Subscribe to client-side auth state for cross-tab reactivity
    const { isAuthenticated: clientAuth, user: clientUser, isInitialized } = useUser();

    // Use client state once initialized, fall back to server state for initial render
    const isAuthenticated = isInitialized ? clientAuth : serverAuth;
    const user = isInitialized ? (clientUser as User | null) : serverUser;
    return (
        <div className="flex flex-col items-start space-y-4 lg:flex-row lg:items-center lg:space-y-0 lg:space-x-4">
            {isAuthenticated && user ? (
                <UserDropdown user={user} variant="homepage" />
            ) : (
                <>
                    <Button
                        variant="ghost"
                        className="min-h-[44px] min-w-[44px] px-3 md:px-4 text-base hover:accent-foreground justify-start"
                        asChild
                    >
                        <Link href="/signin" onClick={onLinkClick}>
                            <LogInIcon className="w-4 h-4 mr-1 text-foreground hover:text-accent-foreground" />
                            Sign In
                        </Link>
                    </Button>
                    <Button
                        className="min-h-[44px] px-4 md:px-6 text-base justify-start"
                        asChild
                    >
                        <Link href="/signup" onClick={onLinkClick}>
                            <span>Get Started</span>
                        </Link>
                    </Button>
                </>
            )}
        </div>
    );
}