'use client';

import React from 'react';
import { ErrorLogger } from '@/lib/errorLogger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function TeamMembersError({ error, reset }: ErrorPageProps) {
  const params = useParams();
  const teamId = params?.teamId as string;

  React.useEffect(() => {
    ErrorLogger.logClientError(
      error,
      'TeamMembersError',
      undefined,
      typeof window !== 'undefined' ? window.location.pathname : undefined,
      {
        digest: error.digest,
        errorBoundary: 'team-members-error-page',
      }
    );
  }, [error]);

  const errorMessage = process.env.NODE_ENV === 'development' 
    ? error.message || 'An unexpected error occurred'
    : 'An unexpected error occurred while loading team members. Please try again.';

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={teamId ? `/dashboard/teams/${teamId}` : '/dashboard'}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Team Dashboard
        </Link>
        <h1 className="text-3xl font-bold">Team Members</h1>
        <p className="text-muted-foreground mt-2">
          Manage your team members and their roles
        </p>
      </div>

      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 bg-destructive/10 rounded-full flex items-center justify-center mb-4">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="text-lg">Error Loading Team Members</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Error Details</AlertTitle>
              <AlertDescription className="mt-2">
                {errorMessage}
              </AlertDescription>
            </Alert>
            
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
                <Link href={teamId ? `/dashboard/teams/${teamId}` : '/dashboard'}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Team Dashboard
                </Link>
              </Button>
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

