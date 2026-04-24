"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  ArrowRight
} from "lucide-react";
import { useVisiblePlatforms } from "@/hooks/use-visible-platforms";

interface SocialMediaStepProps {
  onNext: () => void;
  onPrevious: () => void;
  isLoading?: boolean;
}

export function SocialMediaStep({ onNext, onPrevious, isLoading }: SocialMediaStepProps) {
  const socialPlatforms = useVisiblePlatforms();

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-semibold">Connect Social Media</CardTitle>
        <CardDescription>
          Connect your social accounts to easily share MP clips
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Coming Soon Banner */}
          <div className="bg-muted/50 rounded-lg p-4 text-center border border-border">
            <div className="flex items-center justify-center mb-2">
              <Clock className="h-5 w-5 text-muted-foreground mr-2" />
              <Badge variant="outline" className="text-sm">
                Coming Soon
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Social media integrations will be available in a future update. 
              You can still use all other features without connecting social accounts.
            </p>
          </div>

          {/* Social Platform Preview */}
          <div className="space-y-3">
            <h3 className="font-medium text-foreground">Upcoming Integrations:</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {socialPlatforms.map((platform) => {
                const IconComponent = platform.icon;
                return (
                  <div
                    key={platform.name}
                    className="flex items-center space-x-3 p-3 rounded-lg border border-border bg-muted/30 opacity-60"
                  >
                    <IconComponent className={`h-5 w-5 ${platform.color}`} />
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

          {/* Info Box */}
          <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
            <h4 className="font-medium text-foreground mb-2">What you&apos;ll be able to do:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Schedule clips to post automatically</li>
              <li>• Add custom captions and hashtags</li>
              <li>• Track engagement and performance</li>
              <li>• Cross-post to multiple platforms</li>
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
        </div>
      </CardContent>
    </Card>
  );
}