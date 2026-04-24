"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function TeamSettingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Team settings error:", error);
  }, [error]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Team Settings</h1>
        <p className="text-muted-foreground">
          Manage settings and preferences for your team
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-xl font-semibold text-foreground mb-2">
            Failed to load team settings
          </h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-md">
            We encountered an error while loading the team settings.
            Please try again or contact support if the problem persists.
          </p>
          <Button onClick={reset} variant="default">
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
