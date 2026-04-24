"use client";

import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function PipelineEvaluationError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Pipeline evaluation error:", error);
  }, [error]);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-4xl font-serif font-bold text-foreground tracking-tight">
          Pipeline Evaluation
        </h1>
        <p className="text-xl text-foreground/80 font-medium leading-relaxed">
          Evaluate auto-detected MP identifications from video segments.
        </p>
      </div>

      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="text-lg">Evaluation Error</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              We encountered an error while loading the evaluation page. This
              could be due to a temporary database issue or network problem.
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
                <Link href="/dashboard">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Dashboard
                </Link>
              </Button>
            </div>

            <div className="pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                If the problem persists, please check that processing run IDs
                are configured in the constants file.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
