"use client";

import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw, Home, Settings } from "lucide-react";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to your Parliament Connect dashboard. Manage your clips and track your parliamentary activity.
        </p>
      </div>
      
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="text-lg">Dashboard Error</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              We encountered an error while loading your dashboard. This could be due to a temporary issue with your data or connection.
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
              
              <div className="flex gap-2">
                <Button variant="outline" asChild className="flex-1">
                  <Link href="/dashboard/settings">
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </Link>
                </Button>
                
                <Button variant="outline" asChild className="flex-1">
                  <Link href="/dashboard/my-clips">
                    <Home className="h-4 w-4 mr-2" />
                    My Clips
                  </Link>
                </Button>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                If the problem persists, try checking your internet connection or contact support.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}