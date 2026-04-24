"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorLogger } from "@/lib/errorLogger";

export default function TermsAndConditionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLogger.logClientError(
      error,
      "TermsAndConditionsError",
      undefined,
      typeof window !== "undefined" ? window.location.pathname : undefined,
      { digest: error.digest, errorBoundary: "terms-and-conditions-error-page" },
    );
  }, [error]);

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md border-destructive/20">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-destructive/10 p-3">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-2xl">Terms unavailable</CardTitle>
          <CardDescription className="text-base mt-2">
            We couldn&apos;t load the Terms &amp; Conditions right now.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={reset} className="w-full">
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
