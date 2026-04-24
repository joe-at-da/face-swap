"use client";

import { useEffect, useState } from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function MobileTriggerWrapper() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div className="md:hidden w-full flex justify-end p-4 pb-0">
      <SidebarTrigger />
    </div>
  );
}
