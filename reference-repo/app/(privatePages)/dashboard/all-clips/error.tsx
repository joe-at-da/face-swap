"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { ErrorLogger } from "@/lib/errorLogger";

export default function AllClipsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLogger.logClientError(error, "AllClipsPage");
  }, [error]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-foreground pt-4">All Parliament Clips</h1>

      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Something went wrong
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            We encountered an error while loading the clips.
          </p>
          {error.digest && (
            <p className="text-xs text-muted-foreground">
              Error ID: {error.digest}
            </p>
          )}
          <div className="flex gap-3">
            <Button onClick={reset} className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
            <Button
              variant="outline"
              onClick={() => window.history.back()}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Go back
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
