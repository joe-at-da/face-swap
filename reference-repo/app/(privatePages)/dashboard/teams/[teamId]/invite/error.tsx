"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const params = useParams();
  const teamId = params.teamId as string;

  return (
    <div className="space-y-6">
      <Card className="border-destructive/20">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-destructive/10 p-3">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-2xl">Unable to Send Invitation</CardTitle>
          <CardDescription className="text-base mt-2">
            An error occurred while trying to send the team invitation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <Button
              onClick={reset}
              variant="outline"
              className="flex-1"
            >
              Try Again
            </Button>
            <Button asChild className="flex-1">
              <Link href={`/dashboard/teams/${teamId}/members`}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Members
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}