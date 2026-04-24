"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Share,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { type PlatformWithUI } from "@/lib/platformHelpers";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";
import { useVideoSize } from "@/hooks/use-video-size";
import { useSocialMediaPolling, ConnectedPlatform } from "@/hooks/use-social-media-polling";
import { useTeamSocialMediaPolling } from "@/hooks/use-team-social-media-polling";

// Merged type that combines static platform UI data with dynamic connection data
type MergedPlatform = PlatformWithUI & Partial<ConnectedPlatform>;
import { ShareDialog } from "./share-dialog";
import { ConnectBlueskyDialog } from "./connect-bluesky-dialog";
import { connectSocialMediaPlatformAction } from "@/app/actions/postizActions";
import { toast } from "sonner";

interface SocialShareButtonsProps {
  clipUrl: string | null;
  verticalClipUrl: string | null;
  duration: string | null;
  mpName: string;
  clipId: string;
  teamId?: string | null;
  description?: string | null;
}

const BLUESKY_MAX_SIZE_BYTES = 100 * 1024 * 1024; // 100 MB
const BLUESKY_MAX_DURATION_SECONDS = 180; // 3 minutes

function parseDurationToSeconds(duration: string | null): number | null {
  if (!duration) return null;
  const parts = duration.split(":");
  if (parts.length === 3) {
    // HH:MM:SS or HH:MM:SS.mmm format (from DB)
    const hours = parseInt(parts[0]);
    const minutes = parseInt(parts[1]);
    const seconds = parseFloat(parts[2]);
    if (Number.isNaN(hours) || Number.isNaN(minutes) || Number.isNaN(seconds)) return null;
    return hours * 3600 + minutes * 60 + seconds;
  }
  if (parts.length === 2) {
    // MM:SS format
    const minutes = parseInt(parts[0]);
    const seconds = parseFloat(parts[1]);
    if (Number.isNaN(minutes) || Number.isNaN(seconds)) return null;
    return minutes * 60 + seconds;
  }
  return null;
}

export function SocialShareButtons({
  clipUrl,
  verticalClipUrl,
  duration,
  mpName,
  clipId,
  teamId,
  description,
}: SocialShareButtonsProps) {
  const staticPlatforms = useVisiblePlatforms();
  const { horizontalSizeBytes, verticalSizeBytes } = useVideoSize(clipUrl, verticalClipUrl);

  // Check Bluesky limits
  const durationSeconds = parseDurationToSeconds(duration);
  const exceedsDuration = durationSeconds !== null && durationSeconds > BLUESKY_MAX_DURATION_SECONDS;
  // Bluesky is a vertical platform: share-dialog sends verticalClipUrl when available, else clipUrl
  // null means API failed — don't block sharing (Bluesky API rejects oversized uploads server-side)
  const blueskyActualSizeBytes = verticalClipUrl ? verticalSizeBytes : horizontalSizeBytes;
  const exceedsSize = blueskyActualSizeBytes !== null && blueskyActualSizeBytes > BLUESKY_MAX_SIZE_BYTES;
  const isBlueskyLimitsExceeded = exceedsDuration || exceedsSize;

  const getBlueskyDisabledReason = () => {
    const reasons: string[] = [];
    if (exceedsDuration) reasons.push("longer than 3 minutes");
    if (exceedsSize) reasons.push("larger than 100 MB");
    return `Video is ${reasons.join(" and ")} — exceeds Bluesky limits`;
  };

  // Use team polling if teamId is provided, otherwise use personal polling
  const personalPolling = useSocialMediaPolling({
    pollingInterval: 30000,
    enabled: !teamId,
  });

  const teamPolling = useTeamSocialMediaPolling({
    teamId: teamId || "",
    pollingInterval: 30000,
    enabled: !!teamId,
  });

  // Select the appropriate polling result
  const { platforms, isLoading, error, refetch } = teamId ? teamPolling : personalPolling;
  const ownerName = teamId && 'ownerName' in teamPolling ? teamPolling.ownerName : null;

  const [selectedPlatform, setSelectedPlatform] = useState<{
    name: string;
    identifier: string;
    integrationId: string;
    icon: React.ComponentType<{ className?: string }>;
  } | null>(null);
  const [isBlueskyDialogOpen, setIsBlueskyDialogOpen] = useState(false);

  // Merge static platform data with dynamic connection data
  const mergedPlatforms: MergedPlatform[] = staticPlatforms
    .map((staticPlatform) => {
      const dynamicPlatform = platforms.find(
        (p) => p.identifier === staticPlatform.identifier
      );

      return {
        ...staticPlatform,
        ...dynamicPlatform,
      };
    })
    .sort((a, b) => {
      // Sort: Twitter first, then Bluesky, then others
      if (a.identifier === "x") return -1;
      if (b.identifier === "x") return 1;
      if (a.identifier === "bluesky") return -1;
      if (b.identifier === "bluesky") return 1;
      return 0;
    });

  const handleShareClick = (platform: {
    name: string;
    identifier: string;
    integrationId?: string;
    inBetweenSteps?: boolean;
    icon: React.ComponentType<{ className?: string }>;
  }) => {
    // For Facebook: Block sharing if page not selected (inBetweenSteps=true)
    if (platform.identifier === "facebook" && platform.inBetweenSteps) {
      toast.error(
        "Please select a Facebook page first. Go to your profile settings to complete setup.",
        { duration: 6000 }
      );
      return;
    }

    if (platform.integrationId) {
      setSelectedPlatform({
        name: platform.name,
        identifier: platform.identifier,
        integrationId: platform.integrationId,
        icon: platform.icon,
      });
    }
  };

  const handleShareSuccess = () => {
    // Optionally refetch connection status or update UI
    refetch();
  };

  // Open Facebook page selector popup for when app is connected but page not selected
  const openFacebookPageSelector = () => {
    const width = 500;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      "/integrations/social/facebook",
      "facebook-page-selection",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    if (!popup) {
      toast.error("Popup blocked. Please allow popups for this site.");
      return;
    }

    // Listen for completion message from page selector
    const handlePageSelectionMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === "facebook-oauth-complete") {
        window.removeEventListener("message", handlePageSelectionMessage);
        toast.success("Facebook page selected successfully!");
        refetch();
      }
    };
    window.addEventListener("message", handlePageSelectionMessage);

    // Poll for popup close as fallback
    const checkPopupClosed = setInterval(() => {
      if (popup.closed) {
        clearInterval(checkPopupClosed);
        window.removeEventListener("message", handlePageSelectionMessage);
        refetch();
      }
    }, 500);
  };

  // Open YouTube channel selector popup for when app is connected but channel not selected
  const openYouTubeChannelSelector = () => {
    const width = 500;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      "/integrations/social/youtube",
      "youtube-channel-selection",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    if (!popup) {
      toast.error("Popup blocked. Please allow popups for this site.");
      return;
    }

    // Listen for completion message from channel selector
    const handleChannelSelectionMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === "youtube-oauth-complete") {
        window.removeEventListener("message", handleChannelSelectionMessage);
        toast.success("YouTube channel selected successfully!");
        refetch();
      }
    };
    window.addEventListener("message", handleChannelSelectionMessage);

    // Poll for popup close as fallback
    const checkPopupClosed = setInterval(() => {
      if (popup.closed) {
        clearInterval(checkPopupClosed);
        window.removeEventListener("message", handleChannelSelectionMessage);
        refetch();
      }
    }, 500);
  };

  const handleConnectClick = async (platformIdentifier: string) => {
    if (platformIdentifier === "bluesky") {
      // For Bluesky, open only the Bluesky connection dialog
      setIsBlueskyDialogOpen(true);
      return;
    }

    // For other platforms (like X/Twitter), connect directly - same as settings page
    try {
      const response = await connectSocialMediaPlatformAction(platformIdentifier);

      if (response.error) {
        toast.error(`Failed to connect: ${response.error}`);
        return;
      }

      if (response.data) {
        // Open OAuth URL in a new window
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;

        const popup = window.open(
          response.data,
          "oauth",
          `width=${width},height=${height},left=${left},top=${top}`
        );

        if (!popup) {
          toast.error(
            "Popup blocked. Please allow popups for this site to connect."
          );
          return;
        }

        // Poll for window close and refresh data
        const checkPopupClosed = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkPopupClosed);
            // Refresh connection status after popup closes
            refetch();
          }
        }, 500);

        toast.success("Opening connection window...");
      }
    } catch (err) {
      toast.error(
        `Failed to connect: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    }
  };


  if (!clipUrl && !verticalClipUrl) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-32">
          <div className="text-center space-y-2">
            <Share className="h-6 w-6 mx-auto text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Sharing will be available when clip processing is complete
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="border">
        <CardHeader >
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-3">
              <div className="p-1 rounded bg-slate-200">
                <ExternalLink className="h-5 w-5 text-primary" />
              </div>
              <span className="font-sans font-bold text-lg">Share to Social Media</span>

            </CardTitle>

          </div>
          <CardDescription className="text-sm text-muted-foreground">Share your clip to any connected platform — or link more accounts to expand your reach.</CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 p-4">
          {error && (
            <div className="p-3 border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800/50 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <p className="text-xs text-red-700 dark:text-red-300">
                  {error}
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center gap-3 flex-wrap">
            {isLoading && platforms.length === 0
              ? // Show skeletons on initial load
              Array.from({ length: 2 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-12 rounded-lg" />
              ))
              : mergedPlatforms.map((platform) => {
                const Icon = platform.icon;
                // Facebook/YouTube with inBetweenSteps=true means app connected but page/channel not selected
                const isPageOrChannelNotSelected =
                  (platform.identifier === "facebook" || platform.identifier === "youtube") && platform.inBetweenSteps;
                // Visual disabled state: only for actual limit violations (not during loading)
                const isBlueskyVisuallyLimited = platform.identifier === "bluesky" && isBlueskyLimitsExceeded;
                // Interaction blocking: only block share for actual limit violations when connected
                const isBlueskyLimited = platform.identifier === "bluesky" && isBlueskyLimitsExceeded && platform.isConnected;

                const buttonElement = (
                  <button
                    key={platform.identifier}
                    onClick={() => {
                      // Facebook with inBetweenSteps=true: Open page selector (not OAuth)
                      if (platform.identifier === "facebook" && platform.inBetweenSteps) {
                        openFacebookPageSelector();
                        return;
                      }
                      // YouTube with inBetweenSteps=true: Open channel selector (not OAuth)
                      if (platform.identifier === "youtube" && platform.inBetweenSteps) {
                        openYouTubeChannelSelector();
                        return;
                      }

                      if (platform.isConnected && platform.integrationId) {
                        // Block share when Bluesky limits exceeded, but allow connect
                        if (isBlueskyLimited) return;
                        handleShareClick(platform);
                      } else {
                        handleConnectClick(platform.identifier);
                      }
                    }}
                    className={`relative flex items-center justify-center h-12 w-12 rounded-lg transition-colors ${
                      platform.comingSoon || isBlueskyVisuallyLimited
                        ? "opacity-50 cursor-not-allowed bg-slate-200"
                        : isPageOrChannelNotSelected
                          ? "bg-amber-100 hover:bg-amber-200 cursor-pointer border-2 border-amber-300"
                          : "bg-slate-200 hover:bg-slate-300 cursor-pointer"
                      }`}
                    title={
                      isBlueskyVisuallyLimited
                        ? getBlueskyDisabledReason()
                        : platform.comingSoon
                          ? `${platform.name} - Coming Soon`
                          : isPageOrChannelNotSelected
                            ? `${platform.name} - ${platform.identifier === "youtube" ? "Channel" : "Page"} not selected`
                            : platform.name
                    }
                    disabled={platform.comingSoon}
                    aria-disabled={isBlueskyVisuallyLimited || undefined}
                  >
                    {/* Always show platform icon */}
                    <Icon
                      className={`h-6 w-6 ${
                        platform.comingSoon || isBlueskyVisuallyLimited
                          ? "text-muted-foreground/50"
                          : isPageOrChannelNotSelected
                            ? "text-amber-600"
                            : "text-primary"
                        }`}
                    />

                    {/* Show warning badge for Facebook/YouTube with page/channel not selected */}
                    {isPageOrChannelNotSelected && (
                      <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-amber-500 border-2 border-background flex items-center justify-center">
                        <AlertCircle className="h-3 w-3 text-white" />
                      </div>
                    )}

                    {/* Show error badge for Bluesky when limits exceeded (not during loading) */}
                    {isBlueskyVisuallyLimited && isBlueskyLimitsExceeded && (
                      <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-destructive border-2 border-background flex items-center justify-center">
                        <AlertCircle className="h-3 w-3 text-destructive-foreground" />
                      </div>
                    )}

                    {/* Show profile picture badge when connected (and not in between steps or limits exceeded) */}
                    {platform.isConnected && platform.picture && !isPageOrChannelNotSelected && !(isBlueskyVisuallyLimited && isBlueskyLimitsExceeded) && (
                      <Avatar className="absolute -bottom-1.5 -right-1.5 h-7 w-7 border-2 border-background">
                        <AvatarImage
                          src={platform.picture}
                          alt={platform.profileName || platform.name}
                        />
                        <AvatarFallback className="bg-slate-300 text-xs">
                          {platform.profileName?.[0] || platform.name[0]}
                        </AvatarFallback>
                      </Avatar>
                    )}
                  </button>
                );

                if (isBlueskyLimited && isBlueskyLimitsExceeded) {
                  return (
                    <Popover key={platform.identifier}>
                      <PopoverTrigger asChild>
                        <span>{buttonElement}</span>
                      </PopoverTrigger>
                      <PopoverContent className="w-72" side="top">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
                            <p className="font-semibold text-sm">Bluesky Sharing Unavailable</p>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {getBlueskyDisabledReason()}. Bluesky limits videos to 100 MB and 3 minutes.
                          </p>
                        </div>
                      </PopoverContent>
                    </Popover>
                  );
                }

                return buttonElement;
              })}
          </div>
        </CardContent>
      </Card>

      {/* Share Dialog */}
      {selectedPlatform && (
        <ShareDialog
          platform={selectedPlatform}
          clipData={{
            clipUrl,
            verticalClipUrl,
            mpName,
            clipId,
            description,
          }}
          open={!!selectedPlatform}
          onOpenChange={(open) => !open && setSelectedPlatform(null)}
          onSuccess={handleShareSuccess}
          teamId={teamId}
          teamOwnerName={ownerName}
        />
      )}

      {/* Bluesky Connection Dialog */}
      <ConnectBlueskyDialog
        open={isBlueskyDialogOpen}
        onOpenChange={setIsBlueskyDialogOpen}
        onRefetch={refetch}
      />
    </>
  );
}
