"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import Link from "next/link";

export default function TeamDashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Team dashboard error:", error);
  }, [error]);

  return (
    <div className="container max-w-3xl py-10">
      <Card className="border-destructive">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-destructive" />
            <CardTitle>Unable to Load Team</CardTitle>
          </div>
          <CardDescription>
            We couldn&apos;t load the team dashboard. This might happen if the team doesn&apos;t exist or you don&apos;t have access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {error.message || "An unexpected error occurred while loading the team."}
            </p>
            <div className="flex gap-3">
              <Button onClick={reset} variant="outline">
                Try Again
              </Button>
              <Button asChild>
                <Link href="/dashboard">Back to Dashboard</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}