"use client";

import { useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Logo } from "@/components/logo";

export default function TeamSetupError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Team setup error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Logo />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-16">
        <div className="flex items-center justify-center">
          <Card className="w-full max-w-md">
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="rounded-full bg-destructive/10 p-3">
                  <AlertCircle className="h-6 w-6 text-destructive" />
                </div>
              </div>
              <CardTitle className="text-2xl">Something went wrong</CardTitle>
              <CardDescription className="text-base mt-2">
                {error.message ||
                  "An error occurred while setting up your team account"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={reset} className="w-full" variant="default">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try again
              </Button>
              <Button
                onClick={() => (window.location.href = "/dashboard")}
                className="w-full"
                variant="outline"
              >
                Go to Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
