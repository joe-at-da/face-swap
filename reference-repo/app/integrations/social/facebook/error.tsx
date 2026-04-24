"use client";

import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

export default function FacebookCallbackError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const handleClose = () => {
    if (window.opener) {
      window.opener.postMessage(
        {
          type: "facebook-oauth-complete",
          status: "error",
        },
        window.location.origin
      );
    }
    window.close();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center">
          <AlertCircle className="h-6 w-6 text-destructive" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-semibold">Something went wrong</h2>
          <p className="text-muted-foreground text-sm">
            {error.message || "An unexpected error occurred."}
          </p>
        </div>
        <div className="space-y-2">
          <Button onClick={reset} className="w-full">
            Try Again
          </Button>
          <Button variant="outline" onClick={handleClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
