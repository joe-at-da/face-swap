"use client";

import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

export default function PipelineEvaluationResultsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Pipeline evaluation results error:", error);
  }, [error]);

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <Card className="border-destructive">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <CardTitle>Failed to Load Results</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              We encountered an error while loading the evaluation results. This
              could be due to a network issue or a problem with the data.
            </p>
            {error.message && (
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm font-mono">{error.message}</p>
              </div>
            )}
            <div className="flex gap-2">
              <Button onClick={reset}>Try Again</Button>
              <Button variant="outline" onClick={() => window.location.href = "/dashboard"}>
                Go to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
