"use client";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import NavLinks from "./nav-links";
import ActionButtons from "./action-buttons";
import { X } from "lucide-react";
import type { User } from "@supabase/supabase-js";
import { useUser } from "@/stores/hooks/useUser";

interface MobileMenuProps {
    isOpen: boolean;
    onClose: () => void;
    isAuthenticated: boolean;
    user?: User | null;
}

export default function MobileMenu({ isOpen, onClose, isAuthenticated: serverAuth, user: serverUser }: MobileMenuProps) {
    // Subscribe to client-side auth state for cross-tab reactivity
    const { isAuthenticated: clientAuth, user: clientUser, isInitialized } = useUser();

    // Use client state once initialized, fall back to server state for initial render
    const isAuthenticated = isInitialized ? clientAuth : serverAuth;
    const user = isInitialized ? (clientUser as User | null) : serverUser;

    return (
        <>
            {/* Backdrop */}
            <div
                className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
                    }`}
                onClick={onClose}
            />

            {/* Mobile Menu Panel */}
            <div
                className={`fixed top-0 left-0 h-full w-80 bg-white z-50 transform transition-transform duration-300 ease-in-out ${isOpen ? "translate-x-0" : "-translate-x-full"
                    }`}
            >
                <div className="flex flex-col h-full">
                    {/* Header */}
                    <div className="flex items-center justify-between p-6">
                        <Logo />
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onClose}
                            className="p-2 "
                        >
                            <X style={{ width: '24px', height: '24px' }} className="w-5 h-5 text-foreground" />
                        </Button>
                    </div>

                    {/* Navigation Links */}
                    <div className="flex-col space-y-6 p-6 block lg:hidden">
                        <NavLinks onLinkClick={onClose} />
                    </div>
                    {/* Action Buttons */}
                    <div className="mt-4 px-6">
                        <ActionButtons
                            isAuthenticated={isAuthenticated}
                            user={user}
                            onLinkClick={onClose}
                        />
                    </div>
                </div>
            </div>
        </>
    );
}
