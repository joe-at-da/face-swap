"use client";

import { useState } from "react";
import { usePostHog } from "posthog-js/react";
import { PublicClipViewer, type PublicClipViewerRef } from "./public-clip-viewer";
import { ClipPageHeader } from "./clip-page-header";
import { ShareClipDialog } from "./share-clip-dialog";
import { ReportClipDialog } from "./report-clip-dialog";
import { toast } from "sonner";
import type { PublicClipData } from "@/types/user-clips";

interface PublicClipInteractiveProps {
  clip: PublicClipData;
  clipId: string;
  publicUrl: string;
  pageTitle: string;
}

// Create a shared ref object that both components can use
export const sharedVideoViewerRef = { current: null as PublicClipViewerRef | null };

export function PublicClipInteractive({
  clipId,
  publicUrl,
  pageTitle,
}: PublicClipInteractiveProps) {
  const posthog = usePostHog();
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    // Prevent double-clicking
    if (isDownloading) {
      return;
    }

    if (!sharedVideoViewerRef.current) {
      toast.error("Video player not ready");
      return;
    }

    const videoUrl = sharedVideoViewerRef.current.getCurrentVideoUrl();
    if (!videoUrl) {
      toast.error("No video URL available");
      return;
    }

    setIsDownloading(true);

    try {
      toast.info("Downloading video...");

      // Fetch the video blob
      const response = await fetch(videoUrl);
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `parliament-clip-${clipId}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Track successful download
      posthog.capture("clip_downloaded", {
        clip_id: clipId,
        source: "public_clip_page",
        format: "mp4",
      });

      toast.success("Video downloaded successfully");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download video");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <>
      <ClipPageHeader
        onReportClick={() => setReportDialogOpen(true)}
        onShareClick={() => setShareDialogOpen(true)}
        onDownloadClick={handleDownload}
        isDownloading={isDownloading}
      />
      <ReportClipDialog
        clipId={clipId}
        open={reportDialogOpen}
        onOpenChange={setReportDialogOpen}
      />
      <ShareClipDialog
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        clipUrl={publicUrl}
        clipTitle={pageTitle}
      />
    </>
  );
}

// Video viewer component that shares ref with the interactive component
export function PublicClipVideoViewer({
  clip,
}: {
  clip: PublicClipData;
}) {
  const mpData = clip.parliament_member_clips?.parliament_members;
  
  return (
    <PublicClipViewer
      ref={(r) => {
        sharedVideoViewerRef.current = r;
      }}
      clipUrl={clip.clip_url}
      verticalClipUrl={clip.vertical_clip_url}
      thumbnailUrl={clip.thumbnail_url}
      verticalThumbnailUrl={clip.vertical_thumbnail_url}
      duration={clip.duration}
      mpName={mpData?.full_title || mpData?.display_name || undefined}
      constituency={mpData?.constituency_name || null}
      profileImage={mpData?.profile_image || null}
    />
  );
}
