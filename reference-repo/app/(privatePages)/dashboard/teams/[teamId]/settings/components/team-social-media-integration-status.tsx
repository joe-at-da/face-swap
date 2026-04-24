"use client";

import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Info,
} from "lucide-react";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";
import { useTeamSocialMediaPolling } from "@/hooks/use-team-social-media-polling";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface TeamSocialMediaIntegrationStatusProps {
  teamId: string;
  teamName: string;
}

export function TeamSocialMediaIntegrationStatus({
  teamId,
  teamName,
}: TeamSocialMediaIntegrationStatusProps) {
  const staticPlatforms = useVisiblePlatforms();
  const { platforms, isLoading, error, postizNotSetup, ownerName, refetch } =
    useTeamSocialMediaPolling({
      teamId,
      pollingInterval: 10000,
      enabled: true,
    });

  // Merge static platform data with dynamic connection data
  const mergedPlatforms = staticPlatforms.map((staticPlatform) => {
    const dynamicPlatform = platforms.find(
      (p) => p.identifier === staticPlatform.identifier
    );

    return {
      ...staticPlatform,
      ...dynamicPlatform,
    };
  });

  // Show setup required state if Postiz not setup for team owner
  if (postizNotSetup) {
    return (
      <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20 dark:border-orange-800/50">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-orange-600" />
            <CardTitle className="text-base font-medium text-orange-800 dark:text-orange-200">
              Team Social Media Integration
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-orange-700 dark:text-orange-300">
            Social media integration is not yet set up for this team.
          </p>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs">
              The team owner ({ownerName || "Team Owner"}) needs to complete their account setup
              and connect social media platforms before team members can post on behalf of the team.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <div>
              <CardTitle className="text-base font-medium">
                Team Social Media Integration
              </CardTitle>
              <CardDescription className="text-xs mt-1">
                Posting as {teamName} via {ownerName || "team owner"}&apos;s connected accounts
              </CardDescription>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="h-8 w-8 p-0 flex items-center justify-center rounded-md hover:bg-muted transition-colors"
            aria-label="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
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

        <Alert className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800/50">
          <Info className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-xs text-blue-700 dark:text-blue-300">
            Team social media posts will be made using {ownerName || "the team owner"}&apos;s connected
            accounts. Only the team owner can connect or disconnect platforms.
          </AlertDescription>
        </Alert>

        <div className="grid gap-3">
          {isLoading && platforms.length === 0
            ? // Show skeletons on initial load
              Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="flex items-center space-x-3 text-sm">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))
            : mergedPlatforms.map((platform) => {
                const Icon = platform.icon;

                return (
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
                            <Icon className="h-5 w-5" />
                          </AvatarFallback>
                        </Avatar>
                        {/* Small platform icon badge */}
                        <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-background border-2 border-background flex items-center justify-center">
                          <Icon className="h-3 w-3 text-primary" />
                        </div>
                      </div>
                    ) : (
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/50">
                        <Icon
                          className={`h-5 w-5 ${
                            platform.comingSoon
                              ? "text-muted-foreground/50"
                              : platform.isConnected
                              ? "text-green-600"
                              : "text-muted-foreground"
                          }`}
                        />
                      </div>
                    )}

                    {/* Platform Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`font-medium ${
                            platform.comingSoon
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
                          {platform.profile && (
                            <span className="ml-1">• {platform.profile}</span>
                          )}
                        </p>
                      ) : !platform.isConnected && platform.toolTip ? (
                        <p className="text-xs text-muted-foreground/50 line-clamp-2">
                          {platform.toolTip}
                        </p>
                      ) : null}
                    </div>

                    {/* Status Badge */}
                    {platform.isConnected ? (
                      <Badge
                        variant="outline"
                        className="text-xs border-green-200 bg-green-50 text-green-700 dark:bg-green-950/20 dark:border-green-800/50 dark:text-green-300"
                      >
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Connected
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        Not Connected
                      </Badge>
                    )}
                  </div>
                );
              })}
        </div>

        <p className="text-xs text-muted-foreground">
          When sharing team clips, posts will be made to the connected platforms above using{" "}
          {ownerName || "the team owner"}&apos;s account.
        </p>
      </CardContent>
    </Card>
  );
}
