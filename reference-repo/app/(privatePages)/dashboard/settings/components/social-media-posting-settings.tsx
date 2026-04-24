"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Calendar,
  BarChart3,
  Sparkles
} from "lucide-react";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";

export function SocialMediaPostingSettings() {
  const socialPlatforms = useVisiblePlatforms();

  const upcomingFeatures = [
    {
      name: "Post Scheduling",
      icon: Calendar,
      description: "Schedule clips to post at optimal times",
    },
    {
      name: "Analytics Dashboard",
      icon: BarChart3,
      description: "Track engagement and reach metrics",
    },
    {
      name: "AI Captions",
      icon: Sparkles,
      description: "Auto-generate captions for your clips",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Social Media Posting</CardTitle>
            <CardDescription>
              Connect social accounts and schedule posts
            </CardDescription>
          </div>
          <Badge variant="outline" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Coming Soon
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Coming Soon Banner */}
        <div className="bg-muted/50 rounded-lg p-4 border border-border">
          <p className="text-sm text-muted-foreground">
            Social media integrations and scheduling features will be available in a future update.
            You&apos;ll be able to connect your accounts, schedule posts, and track analytics all in one place.
          </p>
        </div>

        {/* Social Platform Connections */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">Platform Integrations</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {socialPlatforms.map((platform) => {
              const IconComponent = platform.icon;
              return (
                <div
                  key={platform.name}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/30 opacity-60"
                >
                  <div className={`flex-shrink-0 ${platform.color}`}>
                    <IconComponent className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-foreground">
                      {platform.name}
                    </p>
                    {platform.toolTip && (
                      <p className="text-xs text-muted-foreground truncate">
                        {platform.toolTip}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming Features */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">Planned Features</h3>
          <div className="grid gap-2">
            {upcomingFeatures.map((feature) => {
              const IconComponent = feature.icon;
              return (
                <div
                  key={feature.name}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/20 opacity-70"
                >
                  <div className="flex-shrink-0 text-muted-foreground">
                    <IconComponent className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm text-foreground">
                      {feature.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
          <p className="text-sm text-foreground">
            <strong>Want early access?</strong> Social media features are currently in development.
            Stay tuned for updates on when these integrations will be available.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
