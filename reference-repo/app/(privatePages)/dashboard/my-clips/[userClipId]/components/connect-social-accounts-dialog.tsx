"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { CheckCircle2, Clock, Link as LinkIcon, RefreshCw } from "lucide-react";
import { connectSocialMediaPlatformAction } from "@/app/actions/postizActions";
import {
    blueskyConnectionSchema,
    type BlueskyConnectionData,
} from "@/schemas/socialMediaSchema";
import { toast } from "sonner";

interface Platform {
    name: string;
    identifier: string;
    icon: React.ComponentType<{ className?: string }>;
    isConnected?: boolean;
    picture?: string | null;
    profileName?: string | null;
    toolTip?: string | null;
    comingSoon?: boolean;
}

interface ConnectSocialAccountsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    platforms: Platform[];
    selectedPlatformIdentifier?: string | null;
    onRefetch?: () => void;
    onBlueskyConnect?: (data: BlueskyConnectionData) => Promise<void>;
}

export function ConnectSocialAccountsDialog({
    open,
    onOpenChange,
    platforms,
    selectedPlatformIdentifier,
    onRefetch,
    onBlueskyConnect,
}: ConnectSocialAccountsDialogProps) {
    const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
    const [openBlueskyDialog, setOpenBlueskyDialog] = useState(false);

    const blueskyForm = useForm<BlueskyConnectionData>({
        resolver: zodResolver(blueskyConnectionSchema),
        defaultValues: {
            service: "https://bsky.social",
            identifier: "",
            password: "",
        },
    });

    const handleConnect = async (platform: Platform) => {
        if (platform.identifier === "bluesky") {
            setOpenBlueskyDialog(true);
            return;
        }

        setConnectingPlatform(platform.identifier);

        try {
            const response = await connectSocialMediaPlatformAction(
                platform.identifier
            );

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

                // Store interval ID so it can be cleared from postMessage handler
                let checkPopupClosedInterval: ReturnType<typeof setInterval> | null = null;

                // Listen for postMessage from popup (for multi-step OAuth like Facebook)
                const handleOAuthMessage = (event: MessageEvent) => {
                    if (event.origin !== window.location.origin) return;
                    if (
                        event.data?.type === "facebook-oauth-complete" ||
                        event.data?.type === "youtube-oauth-complete"
                    ) {
                        window.removeEventListener("message", handleOAuthMessage);

                        // Clear the interval when OAuth completes via postMessage
                        if (checkPopupClosedInterval) {
                            clearInterval(checkPopupClosedInterval);
                            checkPopupClosedInterval = null;
                        }

                        if (onRefetch) {
                            onRefetch();
                        }
                        onOpenChange(false);
                    }
                };
                window.addEventListener("message", handleOAuthMessage);

                // Poll for window close as fallback (and cleanup listener)
                checkPopupClosedInterval = setInterval(() => {
                    if (popup.closed) {
                        clearInterval(checkPopupClosedInterval!);
                        checkPopupClosedInterval = null;
                        window.removeEventListener("message", handleOAuthMessage);

                        // For Facebook: Show info toast about page selection
                        // This only runs if postMessage was NOT received (user closed popup early)
                        if (platform.identifier === "facebook") {
                            toast.info(
                                "Facebook app connected! Please select a page from your profile settings to complete setup.",
                                { duration: 6000 }
                            );
                        }

                        // For YouTube: Show info toast about channel selection
                        // This only runs if postMessage was NOT received (user closed popup early)
                        if (platform.identifier === "youtube") {
                            toast.info(
                                "YouTube app connected! Please select a channel from your profile settings to complete setup.",
                                { duration: 6000 }
                            );
                        }

                        // Refresh connection status after popup closes
                        if (onRefetch) {
                            onRefetch();
                        }
                        onOpenChange(false);
                    }
                }, 500);

                toast.success("Opening connection window...");
            }
        } catch (err) {
            toast.error(
                `Failed to connect: ${err instanceof Error ? err.message : "Unknown error"}`
            );
        } finally {
            setConnectingPlatform(null);
        }
    };

    const handleBlueskyConnect = async (data: BlueskyConnectionData) => {
        setConnectingPlatform("bluesky");
        try {
            // Call the provided handler from social-media-integration-status.tsx
            if (onBlueskyConnect) {
                await onBlueskyConnect(data);
            } else {
                // Fallback if handler not provided
                console.log("Bluesky connection data:", data);
                toast.success("Bluesky account connected successfully");
                if (onRefetch) {
                    onRefetch();
                }
            }
            setOpenBlueskyDialog(false);
            blueskyForm.reset();
            onOpenChange(false);
        } catch (err) {
            toast.error(
                `Failed to connect Bluesky: ${err instanceof Error ? err.message : "Unknown error"}`
            );
        } finally {
            setConnectingPlatform(null);
        }
    };

    // Auto-connect when dialog opens with a selected platform
    useEffect(() => {
        if (open && selectedPlatformIdentifier) {
            const platform = platforms.find(p => p.identifier === selectedPlatformIdentifier);
            if (platform && !platform.isConnected) {
                // Trigger connection directly
                if (platform.identifier === "bluesky") {
                    setOpenBlueskyDialog(true);
                } else {
                    handleConnect(platform);
                }
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, selectedPlatformIdentifier]);

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Connect your Social Accounts</DialogTitle>
                        <DialogDescription>
                            Link more social accounts in your Profile Settings to reach a wider
                            audience with every video.
                        </DialogDescription>
                    </DialogHeader>
                    <div>
                        {platforms.map((platform) => {
                            const Icon = platform.icon;
                            const isConnecting = connectingPlatform === platform.identifier;
                            return (
                                <div
                                    key={platform.identifier}
                                    className={`group relative overflow-hidden flex items-center justify-between p-4 rounded-xl transition-all duration-300 ${platform.isConnected ? "bg-card hover:shadow-md" : ""
                                        }`}
                                >
                                    {/* Platform Icon or Profile Picture */}
                                    <div className="flex items-center gap-3">
                                        {platform.isConnected && platform.picture ? (
                                            <div className="relative">
                                                <Avatar className="h-10 w-10 rounded bg-slate-200">
                                                    <AvatarImage
                                                        src={platform.picture}
                                                        alt={platform.profileName || platform.name}
                                                    />
                                                    <AvatarFallback className="bg-slate-200">
                                                        <Icon className="h-5 w-5" />
                                                    </AvatarFallback>
                                                </Avatar>
                                                {/* Small platform icon badge */}
                                                <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded bg-slate-200 border-2 border-background flex items-center justify-center">
                                                    <Icon className="h-3 w-3 text-primary" />
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex h-10 w-10 items-center justify-center rounded bg-slate-200">
                                                <Icon
                                                    className={`h-5 w-5 ${platform.comingSoon
                                                        ? "text-muted-foreground/50"
                                                        : "text-primary"
                                                        }`}
                                                />
                                            </div>
                                        )}

                                        {/* Platform Info */}
                                        <div>
                                            <div className="flex items-center space-x-2">
                                                <span
                                                    className={`font-medium ${platform.comingSoon
                                                        ? "text-muted-foreground/70"
                                                        : "text-foreground"
                                                        }`}
                                                >
                                                    {platform.name}
                                                </span>
                                                {platform.isConnected && (
                                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                                )}
                                            </div>
                                            {platform.isConnected && platform.profileName ? (
                                                <p className="text-xs text-muted-foreground truncate">
                                                    Connected as {platform.profileName}
                                                </p>
                                            ) : !platform.isConnected && platform.toolTip ? (
                                                <p className="text-xs text-muted-foreground/50 truncate max-w-[250px]">
                                                    {platform.toolTip}
                                                </p>
                                            ) : null}
                                        </div>
                                    </div>

                                    {/* Action Button */}
                                    {platform.comingSoon ? (
                                        <Badge variant="outline" className="text-xs shadow-sm">
                                            <Clock className="h-3 w-3 mr-1" />
                                            Coming Soon
                                        </Badge>
                                    ) : platform.isConnected ? (
                                        <span className="text-emerald-800 bg-emerald-200 p-2 rounded font-sans text-base">
                                            Connected
                                        </span>
                                    ) : (
                                        <button
                                            onClick={() => handleConnect(platform)}
                                            disabled={isConnecting}
                                            className="flex items-center gap-1.5 font-sans text-base text-primary hover:text-primary/80 transition-colors cursor-pointer disabled:opacity-50"
                                        >
                                            {isConnecting ? (
                                                <>
                                                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                                    Connecting...
                                                </>
                                            ) : (
                                                <>
                                                    Connect
                                                    <LinkIcon className="h-3.5 w-3.5" />
                                                </>
                                            )}
                                        </button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            className="w-full font-sans text-base border-1 border-primary"
                        >
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Bluesky Connection Dialog */}
            <Dialog
                open={openBlueskyDialog}
                onOpenChange={(open) => {
                    if (!open) {
                        setConnectingPlatform(null);
                        setOpenBlueskyDialog(false);
                        blueskyForm.reset();
                    }
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Connect Bluesky</DialogTitle>
                        <DialogDescription>
                            Enter your Bluesky account credentials to connect your account.
                        </DialogDescription>
                    </DialogHeader>
                    <Form {...blueskyForm}>
                        <form
                            onSubmit={blueskyForm.handleSubmit(handleBlueskyConnect)}
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
                            <DialogFooter>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => {
                                        setConnectingPlatform(null);
                                        setOpenBlueskyDialog(false);
                                        blueskyForm.reset();
                                    }}
                                    disabled={!!connectingPlatform}
                                    className="font-sans text-base border-1 border-primary"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    disabled={!!connectingPlatform}
                                    className="bg-primary text-primary-foreground hover:bg-primary/90 font-sans text-base"
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
                            </DialogFooter>
                        </form>
                    </Form>
                </DialogContent>
            </Dialog>
        </>
    );
}

