"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function SetupPageError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Setup page error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center space-x-2">
                <h1 className="font-serif text-xl md:text-2xl font-bold text-foreground">
                  Parliament Connect
                </h1>
                <Badge variant="secondary" className="text-xs">Setup</Badge>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
          <Card className="w-full max-w-md mx-auto">
            <CardHeader className="text-center">
              <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-destructive/10 rounded-full">
                <AlertTriangle className="h-6 w-6 text-destructive" />
              </div>
              <CardTitle className="text-xl font-semibold">Setup Error</CardTitle>
              <CardDescription>
                Something went wrong while loading the setup page
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">
                  <strong>Error:</strong> {error.message}
                </p>
                {error.digest && (
                  <p className="text-xs text-muted-foreground mt-1">
                    <strong>ID:</strong> {error.digest}
                  </p>
                )}
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <Button onClick={reset} className="flex-1">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try Again
                </Button>
                <Button variant="outline" asChild className="flex-1">
                  <Link href="/dashboard">
                    <Home className="mr-2 h-4 w-4" />
                    Go to Dashboard
                  </Link>
                </Button>
              </div>

              <p className="text-xs text-muted-foreground text-center">
                If the problem persists, you can complete your profile setup later from your dashboard settings.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}