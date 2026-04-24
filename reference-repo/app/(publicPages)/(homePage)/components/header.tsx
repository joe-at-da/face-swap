"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import NavLinks from "./nav-links";
import MobileMenu from "./mobile-menu";
import ActionButtons from "./action-buttons";
import { Menu } from "lucide-react";
import type { User } from "@supabase/supabase-js";
import { useUser } from "@/stores/hooks/useUser";

interface HeaderProps {
    isAuthenticated: boolean;
    user?: User | null;
}

export function Header({ isAuthenticated: serverAuth, user: serverUser }: HeaderProps) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Subscribe to client-side auth state for cross-tab reactivity
    const { isAuthenticated: clientAuth, user: clientUser, isInitialized } = useUser();

    // Use client state once initialized, fall back to server state for initial render
    const isAuthenticated = isInitialized ? clientAuth : serverAuth;
    const user = isInitialized ? (clientUser as User | null) : serverUser;

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    const toggleMobileMenu = () => {
        setIsMobileMenuOpen(!isMobileMenuOpen);
    };

    return (
        <header className="sticky top-0 z-50 bg-white">
            <nav className="container mx-auto px-4 md:px-6 lg:px-8" role="navigation" aria-label="Main navigation">
                <div className="flex h-16 items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Logo className="w-[185px] h-[64px]" />
                    </div>
                    {/* Navigation Links - Hidden on mobile, shown on desktop */}
                    <div className="hidden lg:block">
                        <NavLinks />
                    </div>
                    {/* Action Buttons - Hidden on mobile, shown on desktop */}
                    <div className="hidden lg:block">
                        <ActionButtons
                            isAuthenticated={isAuthenticated}
                            user={user}
                        />
                    </div>

                    {/* Mobile Menu Button - Visible on large screens */}
                    <div className="lg:hidden block">
                        <Button
                            variant="ghost"
                            onClick={toggleMobileMenu}
                            className="p-4"
                        >
                            <Menu style={{ width: '24px', height: '24px' }} className="text-foreground" />
                        </Button>
                    </div>
                    {/* Mobile Menu */}
                    <MobileMenu
                        isOpen={isMobileMenuOpen}
                        onClose={closeMobileMenu}
                        isAuthenticated={isAuthenticated}
                        user={user}
                    />
                </div>
            </nav>
        </header>
    );
}
