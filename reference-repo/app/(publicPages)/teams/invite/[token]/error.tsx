"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, Home } from "lucide-react";
import Link from "next/link";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <Card className="w-full max-w-lg border-destructive/20">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-destructive/10 p-3">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-2xl">Invalid Invitation</CardTitle>
          <CardDescription className="text-base mt-2">
            This invitation link appears to be invalid or has expired.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">
              Possible reasons:
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground list-disc list-inside">
              <li>The invitation link has expired (valid for 7 days)</li>
              <li>The invitation has already been accepted</li>
              <li>The link may be incorrect or incomplete</li>
            </ul>
          </div>

          <div className="space-y-3">
            <p className="text-sm text-center text-muted-foreground">
              Please contact the MP who invited you for a new invitation link.
            </p>
            <div className="flex gap-3">
              <Button
                onClick={reset}
                variant="outline"
                className="flex-1"
              >
                Try Again
              </Button>
              <Button asChild className="flex-1">
                <Link href="/">
                  <Home className="mr-2 h-4 w-4" />
                  Go Home
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}