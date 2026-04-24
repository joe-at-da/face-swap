'use client';

import React from 'react';
import { ErrorLogger } from '@/lib/errorLogger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ClipError({ error, reset }: ErrorPageProps) {
  React.useEffect(() => {
    ErrorLogger.logClientError(
      error,
      'ClipError',
      undefined,
      typeof window !== 'undefined' ? window.location.pathname : undefined,
      {
        digest: error.digest,
        errorBoundary: 'clip-error-page',
      }
    );
  }, [error]);

  const errorMessage = process.env.NODE_ENV === 'development' 
    ? error.message || 'An unexpected error occurred'
    : 'An unexpected error occurred while loading this clip. Please try again.';

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-background">
      <Card className="w-full max-w-lg">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3 text-destructive font-serif text-xl sm:text-2xl">
            <AlertTriangle className="h-6 w-6 sm:h-7 sm:w-7 flex-shrink-0" />
            Error Loading Clip
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 px-4 sm:px-6">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle className="font-serif">Error Details</AlertTitle>
            <AlertDescription className="mt-2">
              {errorMessage}
            </AlertDescription>
          </Alert>

          {error.digest && (
            <div className="text-sm text-muted-foreground">
              <p>Error ID: <code className="text-xs bg-muted px-2 py-1 rounded">{error.digest}</code></p>
              <p className="mt-1">This error has been automatically reported to our team.</p>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Button 
              variant="outline" 
              onClick={reset} 
              className="flex-1"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button 
              variant="outline"
              asChild
              className="flex-1"
            >
              <Link href="/dashboard/my-clips">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Clips
              </Link>
            </Button>
            <Button 
              onClick={() => window.location.href = '/'}
              className="flex-1"
            >
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            <p>If this problem persists, please contact support.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

