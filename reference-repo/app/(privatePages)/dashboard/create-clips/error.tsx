"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";

export default function CreateClipsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Create clips page error:', error);
  }, [error]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Create Clips</h1>
        <p className="text-muted-foreground">
          Browse and create clips from parliamentary sessions for your followed MP.
        </p>
      </div>
      
      <Card className="border-red-200 bg-red-50/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-800">
            <AlertCircle className="h-5 w-5" />
            Something went wrong
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-red-700">
            <p className="font-medium">We encountered an error while loading the clips:</p>
            <p className="mt-1 font-mono text-xs bg-red-100 p-2 rounded">
              {error.message || "An unexpected error occurred"}
            </p>
            {error.digest && (
              <p className="mt-2 text-xs text-red-600">
                Error ID: {error.digest}
              </p>
            )}
          </div>
          
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
          
          <div className="text-xs text-muted-foreground border-t pt-4">
            <p>If this problem persists, please:</p>
            <ul className="mt-1 ml-4 list-disc space-y-1">
              <li>Check your internet connection</li>
              <li>Ensure you have selected an MP to follow in your setup</li>
              <li>Try refreshing the page</li>
              <li>Contact support if the issue continues</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}