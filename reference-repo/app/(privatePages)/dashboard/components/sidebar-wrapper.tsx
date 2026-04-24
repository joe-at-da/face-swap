"use client";

import { SidebarProvider } from "@/components/ui/sidebar";
import { useCallback } from "react";

interface SidebarWrapperProps {
  defaultOpen: boolean;
  children: React.ReactNode;
}

export function SidebarWrapper({ defaultOpen, children }: SidebarWrapperProps) {
  // Handle sidebar toggle and persist to Supabase user metadata
  const handleToggle = useCallback((isOpen: boolean) => {
    // Fire-and-forget API call to persist sidebar state
    fetch("/api/settings/sidebar", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        collapsed: !isOpen, // Store collapsed state (true when sidebar is closed)
      }),
    }).catch((error) => {
      // Silently fail - sidebar will still work, just won't persist
      console.error("Error updating sidebar preference:", error);
    });
  }, []);

  return (
    <SidebarProvider defaultOpen={defaultOpen} onToggle={handleToggle}>
      {children}
    </SidebarProvider>
  );
}
