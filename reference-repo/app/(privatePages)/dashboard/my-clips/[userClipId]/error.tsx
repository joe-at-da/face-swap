"use client";

import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function UserClipError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("User clip page error:", error);
  }, [error]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link href="/dashboard/my-clips">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to My Clips
          </Link>
        </Button>
      </div>

      {/* Error Content */}
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="text-3xl font-serif font-bold">Clip not available</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              This clip is currently unavailable. It may still be processing or there was an issue loading it. Please try again or check your My Clips page.
            </p>
            
            {error.digest && (
              <div className="text-xs text-muted-foreground bg-muted p-2 rounded font-mono">
                Error ID: {error.digest}
              </div>
            )}
            
            <div className="flex flex-col gap-2 pt-4">
              <Button onClick={reset} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              
              <Button variant="outline" asChild className="w-full">
                <Link href="/dashboard/my-clips">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to My Clips
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}