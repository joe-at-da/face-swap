"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorLogger } from "@/lib/errorLogger";

export default function DashboardAnalyticsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLogger.logClientError(
      error,
      "DashboardAnalyticsError",
      undefined,
      "/dashboard/analytics",
      { digest: error.digest, errorBoundary: "analytics-error-page" }
    );
  }, [error]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center pt-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle>Analytics couldn&apos;t be loaded</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground">
            The analytics page hit an unexpected error. Retry the request or come
            back after checking the Postiz connection.
          </p>
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
