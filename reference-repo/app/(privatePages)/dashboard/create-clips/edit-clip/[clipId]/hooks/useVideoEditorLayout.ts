"use client";

import { useState, useEffect } from "react";
import { useMediaQuery } from "@/hooks/use-media-query";

const STORAGE_KEY = "video-editor-layout-v1";

interface LayoutState {
  videoSize: number;
  timelineSize: number;
  sidePanelSize: number;
  isSheetOpen: boolean;
  activeTab: string;
  isSidePanelCollapsed: boolean;
}

const DEFAULT_LAYOUT: LayoutState = {
  videoSize: 66,
  timelineSize: 34,
  sidePanelSize: 25,
  isSheetOpen: false,
  activeTab: "clips",
  isSidePanelCollapsed: false,
};

export function useVideoEditorLayout() {
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const isTablet = useMediaQuery("(min-width: 768px) and (max-width: 1023px)");
  const isMobile = useMediaQuery("(max-width: 767px)");

  const [layout, setLayout] = useState<LayoutState>(DEFAULT_LAYOUT);

  // Load saved layout from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setLayout((prev) => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error("Failed to parse saved layout:", error);
      }
    }
  }, []);

  // Save layout to localStorage whenever it changes
  const updateLayout = (updates: Partial<LayoutState>) => {
    setLayout((prev) => {
      const newLayout = { ...prev, ...updates };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newLayout));
      return newLayout;
    });
  };

  // Sheet controls for mobile/tablet
  const openSheet = () => updateLayout({ isSheetOpen: true });
  const closeSheet = () => updateLayout({ isSheetOpen: false });
  const toggleSheet = () => updateLayout({ isSheetOpen: !layout.isSheetOpen });

  // Active tab control
  const setActiveTab = (tab: string) => updateLayout({ activeTab: tab });

  // Panel size controls
  const updatePanelSizes = (sizes: number[]) => {
    if (sizes.length === 2) {
      // Horizontal split: [left panel, side panel]
      updateLayout({
        sidePanelSize: sizes[1],
      });
    }
  };

  // Video/Timeline vertical split controls
  const updateVideoTimelineSizes = (sizes: number[]) => {
    if (sizes.length === 2) {
      updateLayout({
        videoSize: sizes[0],
        timelineSize: sizes[1],
      });
    }
  };

  // Side panel collapse state
  const setSidePanelCollapsed = (collapsed: boolean) => {
    updateLayout({ isSidePanelCollapsed: collapsed });
  };

  // Determine if side panel should be in Sheet based on breakpoint
  const shouldUseSheet = isMobile || isTablet;

  return {
    layout,
    isDesktop,
    isTablet,
    isMobile,
    shouldUseSheet,
    openSheet,
    closeSheet,
    toggleSheet,
    setActiveTab,
    updatePanelSizes,
    updateVideoTimelineSizes,
    setSidePanelCollapsed,
  };
}
