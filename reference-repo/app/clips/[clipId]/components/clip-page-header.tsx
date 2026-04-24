"use client";

import { Share2, Download, Flag, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";

interface ClipPageHeaderProps {
  onShareClick: () => void;
  onDownloadClick: () => void;
  onReportClick: () => void;
  isDownloading?: boolean;
}

export function ClipPageHeader({
  onShareClick,
  onDownloadClick,
  onReportClick,
  isDownloading = false,
}: ClipPageHeaderProps) {
  return (
    <header className="bg-background border-b border-border">
      <div className="container mx-auto px-4 md:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo Section */}
          <Logo className="h-10" />

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={onReportClick}
              className="h-11 w-11"
              aria-label="Report clip"
            >
              <Flag className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onShareClick}
              className="h-11 w-11"
              aria-label="Share clip"
            >
              <Share2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onDownloadClick}
              disabled={isDownloading}
              className="h-11 w-11"
              aria-label={isDownloading ? "Downloading..." : "Download clip"}
            >
              {isDownloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
