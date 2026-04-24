"use client";

import { useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function NoTeamAccessError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to error reporting service
    console.error("No team access page error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <Card className="p-8 md:p-12">
          <div className="space-y-6">
            {/* Icon and Header */}
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <div className="rounded-full bg-destructive/10 p-4">
                  <AlertCircle className="h-12 w-12 text-destructive" />
                </div>
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
                  Something Went Wrong
                </h1>
                <p className="text-lg text-muted-foreground">
                  We encountered an error while loading this page
                </p>
              </div>
            </div>

            {/* Error Details */}
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {error.message || "An unexpected error occurred"}
              </AlertDescription>
            </Alert>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button onClick={reset} className="flex-1" size="lg">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
              <Button asChild variant="outline" className="flex-1" size="lg">
                <Link href="/">
                  <Home className="mr-2 h-4 w-4" />
                  Return to Home
                </Link>
              </Button>
            </div>

            {/* Support Contact */}
            <div className="text-center pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                If this problem persists, please{" "}
                <a
                  href="mailto:support@mpai.com"
                  className="text-primary hover:underline"
                >
                  contact support
                </a>
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
