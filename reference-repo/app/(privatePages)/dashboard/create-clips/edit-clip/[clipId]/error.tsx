"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { ErrorLogger } from "@/lib/errorLogger";

export default function EditClipError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    ErrorLogger.logError(error, {
      component: "EditClipPage",
      action: "render",
      feature: "remotion-editor",
    });
  }, [error]);

  const goBackToClips = () => {
    router.push('/dashboard/create-clips');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Edit Clip</h1>
        <p className="text-muted-foreground">
          Create custom clips by selecting segments from the full parliamentary session.
        </p>
      </div>
      
      <Card className="border-red-200 bg-red-50/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-800">
            <AlertCircle className="h-5 w-5" />
            Failed to load clip editor
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-red-700">
            <p className="font-medium">We encountered an error while loading the clip editor:</p>
            <p className="mt-1 font-mono text-xs bg-red-100 p-2 rounded">
              {error.digest ? "An unexpected error occurred. Please try again." : error.message || "An unexpected error occurred"}
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
              onClick={goBackToClips}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to clips
            </Button>
          </div>
          
          <div className="text-xs text-muted-foreground border-t pt-4">
            <p>This error might occur if:</p>
            <ul className="mt-1 ml-4 list-disc space-y-1">
              <li>The clip you&apos;re trying to edit doesn&apos;t exist</li>
              <li>You don&apos;t have permission to access this clip</li>
              <li>The clip belongs to an MP you&apos;re not following</li>
              <li>There&apos;s a connection issue with the database</li>
            </ul>
            <p className="mt-2">
              Try going back to the clips page and selecting a different clip, or contact support if the problem persists.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}