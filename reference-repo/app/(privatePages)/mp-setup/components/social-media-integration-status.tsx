"use client";

import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Trash2,
  ChevronDown,
  ExternalLink,
} from "lucide-react";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";
import { useSocialMediaPolling } from "@/hooks/use-social-media-polling";
import {
  connectSocialMediaPlatformAction,
  disconnectSocialMediaPlatformAction,
  connectBlueskyAccountAction,
  getBlueskyCredentialsAction,
  disconnectBlueskyAccountAction,
} from "@/app/actions/postizActions";
import {
  blueskyConnectionSchema,
  type BlueskyConnectionData,
} from "@/schemas/socialMediaSchema";
import { toast } from "sonner";

interface SocialMediaIntegrationStatusProps {
  postizCreating?: boolean;
  postizCreated?: boolean;
  postizError?: string | null;
}

export function SocialMediaIntegrationStatus({
  postizCreating = false,
  postizCreated = false,
  postizError = null,
}: SocialMediaIntegrationStatusProps) {
  const staticPlatforms = useVisiblePlatforms();
  const { platforms, isLoading, error, refetch } = useSocialMediaPolling({
    pollingInterval: 10000,
    enabled: postizCreated || !postizCreating, // Only poll when Postiz ready or not creating
  });
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(
    null
  );
  const [disconnectingPlatform, setDisconnectingPlatform] = useState<
    string | null
  >(null);
  const [platformToDisconnect, setPlatformToDisconnect] = useState<{
    identifier: string;
    name: string;
    integrationId: string;
  } | null>(null);
  const [openAddBlueskyAccount, setOpenAddBlueskyAccount] =
    useState<boolean>(false);
  const [blueskyCredentials, setBlueskyCredentials] = useState<{
    service: string;
    identifier: string;
    hasPassword: boolean;
  } | null>(null);
  
  // Track connection attempts to detect success/failure
  interface PendingConnection {
    platformIdentifier: string;
    wasConnected: boolean;
    platformName: string;
    failureTimeoutId?: NodeJS.Timeout;
  }
  const pendingConnectionRef = useRef<PendingConnection | null>(null);

  const blueskyForm = useForm<BlueskyConnectionData>({
    resolver: zodResolver(blueskyConnectionSchema),
    defaultValues: {
      service: "https://bsky.social",
      identifier: "",
      password: "",
    },
  });


  // Trigger refetch when Postiz account is created
  useEffect(() => {
    if (postizCreated) {
      refetch();
    }
  }, [postizCreated, refetch]);

  // Load Bluesky credentials on mount and when Postiz is created
  useEffect(() => {
    const loadBlueskyCredentials = async () => {
      if (!postizCreated) {
        return;
      }

      try {
        const result = await getBlueskyCredentialsAction();
        if (result.error) {
          console.error(
            "[Bluesky UI] Failed to load credentials:",
            result.error
          );
          setBlueskyCredentials(null);
        } else {
          setBlueskyCredentials(result.data);
          console.log("[Bluesky UI] Loaded credentials:", {
            hasCredentials: !!result.data,
            identifier: result.data?.identifier,
          });
        }
      } catch (error) {
        console.error("[Bluesky UI] Error loading credentials:", error);
        setBlueskyCredentials(null);
      }
    };

    loadBlueskyCredentials();
  }, [postizCreated]);

  // Check for connection success/failure after platforms update
  useEffect(() => {
    if (!pendingConnectionRef.current) return;

    const { platformIdentifier, wasConnected, platformName } =
      pendingConnectionRef.current;
    const currentPlatform = platforms.find(
      (p) => p.identifier === platformIdentifier
    );
    const isNowConnected = currentPlatform?.isConnected || false;

    // Only check if we're still in connecting state
    if (connectingPlatform === platformIdentifier) {
      if (isNowConnected && !wasConnected) {
        // Connection succeeded!
        // Clear any pending failure timeout
        if (pendingConnectionRef.current?.failureTimeoutId) {
          clearTimeout(pendingConnectionRef.current.failureTimeoutId);
        }
        toast.success(`Successfully connected to ${platformName}!`);
        setConnectingPlatform(null);
        pendingConnectionRef.current = null;
      }
    }
  }, [platforms, connectingPlatform]);

  const handleConnect = async (platformIdentifier: string) => {
    if (platformIdentifier === "bluesky") {
      setOpenAddBlueskyAccount(true);
      return;
    }

    setConnectingPlatform(platformIdentifier);

    // Store previous connection state to detect changes after OAuth
    const previousPlatform = platforms.find(
      (p) => p.identifier === platformIdentifier
    );
    const wasConnected = previousPlatform?.isConnected || false;
    const platformName =
      staticPlatforms.find((p) => p.identifier === platformIdentifier)?.name ||
      platformIdentifier;

    try {
      const response = await connectSocialMediaPlatformAction(
        platformIdentifier
      );

      if (response.error) {
        toast.error(
          `Failed to connect to ${platformName}: ${response.error}`
        );
        setConnectingPlatform(null);
        return;
      }

      if (!response.data) {
        toast.error(
          `Failed to connect to ${platformName}: No OAuth URL received`
        );
        setConnectingPlatform(null);
        return;
      }

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
        setConnectingPlatform(null);
        return;
      }

      toast.success("Opening connection window...");

      // Store connection attempt info for success/failure detection
      pendingConnectionRef.current = {
        platformIdentifier,
        wasConnected,
        platformName,
      };

      // Poll for window close and check connection status
      const checkPopupClosed = setInterval(async () => {
        if (popup.closed) {
          clearInterval(checkPopupClosed);
          
          // Wait a moment for OAuth callback to complete
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          // Refresh connection status after popup closes
          await refetch();
          
          // Set a timeout to check if connection failed (still not connected after delay)
          // The useEffect will handle success detection
          // We use a ref to track the timeout so we can clear it if connection succeeds
          const failureTimeoutId = setTimeout(() => {
            // Check if we're still waiting for this connection
            if (pendingConnectionRef.current?.platformIdentifier === platformIdentifier) {
              // Still not connected after delay - likely failed or user cancelled
              toast.error(
                `Failed to connect to ${platformName}. Please try again.`
              );
              setConnectingPlatform(null);
              pendingConnectionRef.current = null;
            }
          }, 5000); // Wait 5 seconds after refetch to check for failure
          
          // Store timeout ID in ref so we can clear it on success (handled in useEffect)
          if (pendingConnectionRef.current) {
            pendingConnectionRef.current.failureTimeoutId = failureTimeoutId;
          }
        }
      }, 500);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error";
      
      // Check if it's a network error
      if (err instanceof TypeError && err.message.includes("fetch")) {
        toast.error(
          `Failed to connect to ${platformName}: Network error. Please check your connection and try again.`
        );
      } else {
        toast.error(`Failed to connect to ${platformName}: ${errorMessage}`);
      }
      setConnectingPlatform(null);
    }
  };

  const handleBlueskyAccountAdd = async (data: BlueskyConnectionData) => {
    setConnectingPlatform("bluesky");

    try {
      if (!data.service || !data.identifier || !data.password) {
        const missingFields = [];
        if (!data.service) missingFields.push("service");
        if (!data.identifier) missingFields.push("identifier");
        if (!data.password) missingFields.push("password");
        throw new Error(`Missing required fields: ${missingFields.join(", ")}`);
      }

      const response = await connectBlueskyAccountAction(
        data.service,
        data.identifier,
        data.password
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast.success("Bluesky account connected successfully");

      // Reload Bluesky credentials
      const credentialsResult = await getBlueskyCredentialsAction();
      if (credentialsResult.data) {
        setBlueskyCredentials(credentialsResult.data);
      }

      await refetch();
      setOpenAddBlueskyAccount(false);
      blueskyForm.reset();
    } catch (err) {
      console.error("Failed to connect Bluesky:", err);
      toast.error(
        `Failed to connect Bluesky: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setConnectingPlatform(null);
    }
  };

  const handleDisconnect = async (
    integrationId: string,
    platformName: string
  ) => {
    setDisconnectingPlatform(integrationId);

    try {
      const response = await disconnectSocialMediaPlatformAction(integrationId);

      if (response.error) {
        toast.error(`Failed to disconnect: ${response.error}`);
        return;
      }

      toast.success(`${platformName} disconnected successfully`);
      // Refresh connection status
      refetch();
    } catch (err) {
      toast.error(
        `Failed to disconnect: ${err instanceof Error ? err.message : "Unknown error"
        }`
      );
    } finally {
      setDisconnectingPlatform(null);
      setPlatformToDisconnect(null);
    }
  };

  // Merge static platform data with dynamic connection data
  const mergedPlatforms = staticPlatforms.map((staticPlatform) => {
    const dynamicPlatform = platforms.find(
      (p) => p.identifier === staticPlatform.identifier
    );

    // For Bluesky, check stored credentials if not connected via Postiz
    let isBlueskyConnected = false;
    if (staticPlatform.identifier === "bluesky") {
      isBlueskyConnected = !!blueskyCredentials;
    }

    return {
      ...staticPlatform,
      ...dynamicPlatform,
      // Override isConnected for Bluesky if we have stored credentials
      isConnected:
        staticPlatform.identifier === "bluesky"
          ? isBlueskyConnected || (dynamicPlatform?.isConnected || false)
          : dynamicPlatform?.isConnected || false,
      // Add Bluesky identifier as profileName if connected via stored credentials
      profileName:
        staticPlatform.identifier === "bluesky" && blueskyCredentials
          ? blueskyCredentials.identifier
          : dynamicPlatform?.profileName,
      // Include inBetweenSteps for Facebook/YouTube page/channel selection state
      inBetweenSteps: dynamicPlatform?.inBetweenSteps || false,
    };
  });

  // Function to open Facebook page selector popup
  const openFacebookPageSelector = () => {
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      "/integrations/social/facebook",
      "facebook-page-selection",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    if (popup) {
      // Listen for completion from page selection
      const handlePageSelectionMessage = (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type === "facebook-oauth-complete") {
          window.removeEventListener("message", handlePageSelectionMessage);
          if (event.data.status === "success") {
            toast.success("Facebook page selected successfully!");
          }
          refetch();
        }
      };
      window.addEventListener("message", handlePageSelectionMessage);

      // Poll for popup close
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          window.removeEventListener("message", handlePageSelectionMessage);
          refetch();
        }
      }, 500);
    } else {
      toast.error("Please allow popups to select a Facebook page");
    }
  };

  // Function to open YouTube channel selector popup
  const openYouTubeChannelSelector = () => {
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      "/integrations/social/youtube",
      "youtube-channel-selection",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    if (popup) {
      // Listen for completion from channel selection
      const handleChannelSelectionMessage = (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type === "youtube-oauth-complete") {
          window.removeEventListener("message", handleChannelSelectionMessage);
          if (event.data.status === "success") {
            toast.success("YouTube channel selected successfully!");
          }
          refetch();
        }
      };
      window.addEventListener("message", handleChannelSelectionMessage);

      // Poll for popup close
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          window.removeEventListener("message", handleChannelSelectionMessage);
          refetch();
        }
      }, 500);
    } else {
      toast.error("Please allow popups to select a YouTube channel");
    }
  };

  // Show loading state while Postiz account is being created
  if (postizCreating) {
    return (
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-primary animate-pulse" />
            <CardTitle className="text-base font-medium text-primary">
              Setting up Social Media Integration...
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="flex items-center space-x-3">
                <Skeleton className="h-10 w-10 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="h-8 w-20" />
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Creating your social media management account...
          </p>
        </CardContent>
      </Card>
    );
  }

  // Show error state if Postiz creation failed
  if (postizError) {
    return (
      <Card className="border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800/50">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <CardTitle className="text-base font-medium text-red-800 dark:text-red-200">
              Social Media Integration
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-red-700 dark:text-red-300">
            Failed to set up social media integration: {postizError}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
            className="text-xs"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Retry Setup
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-bold font-sans">
              Social Media Integration
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1 pb-4">
              Connect your social media accounts to start sharing clips.<br />
              Click Connect to authorize access through a secure OAuth flow.
            </p>
          </div>

        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800/50 rounded-lg">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <p className="text-xs text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}

        <div className="grid gap-3">
          {isLoading && platforms.length === 0
            ? // Show skeletons on initial load
            Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="flex items-center space-x-3 text-sm"
              >
                <Skeleton className="h-10 w-10 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="h-8 w-20" />
              </div>
            ))
            : mergedPlatforms.map((platform) => {
              const Icon = platform.icon;
              const isConnecting = connectingPlatform === platform.identifier;

              const platformRow = (
                <div
                  key={platform.identifier}
                  className="flex items-center space-x-3 text-sm"
                >
                  {/* Platform Icon or Profile Picture */}
                  {platform.isConnected && platform.picture ? (
                    <div className="relative">
                      <Avatar className="h-10 w-10">
                        <AvatarImage
                          src={platform.picture}
                          alt={platform.profileName || platform.name}
                        />
                        <AvatarFallback>
                          <Icon className="h-5 w-5 text-slate-600" />
                        </AvatarFallback>
                      </Avatar>
                      {/* Small platform icon badge */}
                      <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded bg-background border-2 border-background flex items-center justify-center">
                        <Icon className="h-3 w-3 text-slate-600" />
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-10 w-10 items-center justify-center rounded bg-muted/50">
                      <Icon
                        className={`h-5 w-5 ${platform.comingSoon
                          ? "text-muted-foreground/50"
                          : "text-slate-600"
                          }`}
                      />
                    </div>
                  )}

                  {/* Platform Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`font-medium ${platform.comingSoon
                          ? "text-muted-foreground/70"
                          : "text-slate-600"
                          }`}
                        >
                          {platform.name}
                        </span>
                        {/* Show checkmark only if fully connected (not inBetweenSteps) */}
                        {((platform.isConnected && !platform.inBetweenSteps) ||
                          (platform.identifier === "bluesky" && blueskyCredentials)) && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                        {/* Show warning icon for Facebook/YouTube when page/channel not selected */}
                        {(platform.identifier === "facebook" || platform.identifier === "youtube") && platform.inBetweenSteps && (
                          <AlertCircle className="h-4 w-4 text-amber-500" />
                        )}
                      </div>
                      {/* Facebook/YouTube: Show "App connected, page/channel not selected" when inBetweenSteps */}
                      {platform.identifier === "facebook" && platform.inBetweenSteps ? (
                        <p className="text-xs text-amber-600 font-medium">
                          App connected - page not selected
                        </p>
                      ) : platform.identifier === "youtube" && platform.inBetweenSteps ? (
                        <p className="text-xs text-amber-600 font-medium">
                          App connected - channel not selected
                        </p>
                      ) : (platform.isConnected ||
                        (platform.identifier === "bluesky" && blueskyCredentials)) &&
                       platform.profileName ? (
                        <p className="text-xs text-muted-foreground truncate">
                          Connected as {platform.profileName}
                          {platform.profile && (
                            <span className="ml-1">• {platform.profile}</span>
                          )}
                        </p>
                      ) : !platform.isConnected &&
                        !(platform.identifier === "bluesky" && blueskyCredentials) &&
                        platform.toolTip ? (
                        <p className="text-xs text-muted-foreground/50 line-clamp-2">
                          {platform.toolTip}
                        </p>
                      ) : null}
                    </div>

                    {/* Action Button */}
                    {platform.comingSoon ? (
                      <Badge variant="outline" className="text-xs">
                        <Clock className="h-3 w-3 mr-1" />
                        Coming Soon
                      </Badge>
                    ) : platform.identifier === "facebook" && platform.inBetweenSteps ? (
                      // Facebook: Show "Select Page" button when app connected but page not selected
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:bg-amber-950/20 dark:border-amber-800/50 dark:text-amber-300"
                        onClick={openFacebookPageSelector}
                      >
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Select Page
                      </Button>
                    ) : platform.identifier === "youtube" && platform.inBetweenSteps ? (
                      // YouTube: Show "Select Channel" button when app connected but channel not selected
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:bg-amber-950/20 dark:border-amber-800/50 dark:text-amber-300"
                        onClick={openYouTubeChannelSelector}
                      >
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Select Channel
                      </Button>
                    ) : platform.isConnected ||
                      (platform.identifier === "bluesky" && blueskyCredentials) ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs border-green-200 bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950/20 dark:border-green-800/50 dark:text-green-300"
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Connected
                            <ChevronDown className="h-3 w-3 ml-1" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={async () => {
                              if (platform.identifier === "bluesky" && blueskyCredentials) {
                                // Handle Bluesky disconnection (remove stored credentials)
                                try {
                                  const result = await disconnectBlueskyAccountAction();
                                  if (result.error) {
                                    toast.error(`Failed to disconnect: ${result.error}`);
                                  } else {
                                    toast.success("Bluesky disconnected successfully");
                                    setBlueskyCredentials(null);
                                    refetch();
                                  }
                                } catch (err) {
                                  toast.error(
                                    `Failed to disconnect: ${
                                      err instanceof Error ? err.message : "Unknown error"
                                    }`
                                  );
                                }
                              } else {
                                // Handle other platforms (Postiz integrations)
                                setPlatformToDisconnect({
                                  identifier: platform.identifier,
                                  name: platform.name,
                                  integrationId: platform.integrationId!,
                                });
                              }
                            }}
                          >
                            <Trash2 className="h-3 w-3 mr-2" />
                            Disconnect
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs"
                        onClick={() => handleConnect(platform.identifier)}
                        disabled={isConnecting}
                      >
                        {isConnecting ? (
                          <>
                            <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Connect
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                );

              return platformRow;
            })}
        </div>
      </CardContent>

      {/* Disconnect Confirmation Dialog */}
      <AlertDialog
        open={!!platformToDisconnect}
        onOpenChange={(open) => !open && setPlatformToDisconnect(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Disconnect {platformToDisconnect?.name}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the connection to your{" "}
              {platformToDisconnect?.name} account. You can reconnect with a
              different account anytime.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (platformToDisconnect) {
                  handleDisconnect(
                    platformToDisconnect.integrationId,
                    platformToDisconnect.name
                  );
                }
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={!!disconnectingPlatform}
            >
              {disconnectingPlatform ? (
                <>
                  <RefreshCw className="h-3 w-3 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                "Disconnect"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={openAddBlueskyAccount}
        onOpenChange={(open) => {
          if (!open) {
            setConnectingPlatform(null);
            setOpenAddBlueskyAccount(false);
            blueskyForm.reset();
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Connect Bluesky</AlertDialogTitle>
            <AlertDialogDescription>
              Enter your Bluesky account credentials to connect your account.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Form {...blueskyForm}>
            <form
              onSubmit={blueskyForm.handleSubmit(handleBlueskyAccountAdd)}
              className="space-y-4"
            >
              <FormField
                control={blueskyForm.control}
                name="service"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Service</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="https://bsky.social"
                        disabled={!!connectingPlatform}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={blueskyForm.control}
                name="identifier"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Identifier</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="example.bsky.social"
                        disabled={!!connectingPlatform}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={blueskyForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder="Enter your password"
                        disabled={!!connectingPlatform}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <AlertDialogFooter>
                <AlertDialogCancel
                  onClick={() => {
                    setConnectingPlatform(null);
                    setOpenAddBlueskyAccount(false);
                    blueskyForm.reset();
                  }}
                >
                  Cancel
                </AlertDialogCancel>
                <Button
                  type="submit"
                  disabled={!!connectingPlatform}
                  className="bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  {connectingPlatform ? (
                    <>
                      <RefreshCw className="h-3 w-3 mr-2 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    "Connect"
                  )}
                </Button>
              </AlertDialogFooter>
            </form>
          </Form>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
