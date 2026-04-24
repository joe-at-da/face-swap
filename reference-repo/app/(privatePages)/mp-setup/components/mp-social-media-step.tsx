"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  ArrowRight,
  Clock,
  Sparkles
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";

interface MpSocialMediaStepProps {
  onNext: () => void;
  onPrevious: () => void;
  isLoading?: boolean;
}

export function MpSocialMediaStep({ onNext, onPrevious, isLoading }: MpSocialMediaStepProps) {
  const socialPlatforms = useVisiblePlatforms();

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="flex justify-center mb-2">
          <Sparkles className="h-8 w-8 text-primary" />
        </div>
        <CardTitle className="text-2xl font-semibold">Social Media Integration</CardTitle>
        <CardDescription>
          Connect your social media accounts for automated posting
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Coming Soon Banner */}
        <div className="p-4 border border-orange-200 bg-orange-50 dark:bg-orange-950/20 dark:border-orange-800/50 rounded-lg">
          <div className="flex items-center space-x-2 mb-2">
            <Clock className="h-4 w-4 text-orange-600" />
            <span className="text-sm font-medium text-orange-800 dark:text-orange-200">
              Feature Coming Soon
            </span>
          </div>
          <p className="text-xs text-orange-700 dark:text-orange-300">
            Social media integration is currently in development. You&apos;ll be notified when it becomes available for MPs.
          </p>
        </div>

        {/* Social Media Platforms */}
        <div className="grid gap-4">
          {socialPlatforms.map((platform) => {
            const Icon = platform.icon;
            return (
              <div
                key={platform.name}
                className={cn(
                  "flex items-center space-x-4 p-4 rounded-lg border transition-colors",
                  "opacity-50 cursor-not-allowed bg-muted/50 border-border"
                )}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                  <Icon className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium text-muted-foreground">{platform.name}</h4>
                    <Badge variant="outline" className="text-xs">
                      Coming Soon
                    </Badge>
                  </div>
                  {platform.toolTip && (
                    <p className="text-sm text-muted-foreground">
                      {platform.toolTip}
                    </p>
                  )}
                </div>
                <Button variant="outline" disabled className="opacity-50">
                  Connect
                </Button>
              </div>
            );
          })}
        </div>

        {/* Information */}
        <div className="p-4 border border-primary/20 bg-primary/5 rounded-lg">
          <h4 className="text-sm font-medium text-primary mb-2">What&apos;s Coming:</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• One-click posting to multiple platforms</li>
            <li>• Automated scheduling for optimal engagement</li>
            <li>• Platform-specific formatting and hashtags</li>
            <li>• Analytics and performance tracking</li>
          </ul>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-4">
          <Button 
            type="button" 
            variant="outline" 
            onClick={onPrevious}
            disabled={isLoading}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>
          
          <Button 
            type="button"
            onClick={onNext}
            disabled={isLoading}
          >
            Continue
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}