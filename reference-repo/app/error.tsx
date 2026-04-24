'use client';

import React from 'react';
import { ErrorLogger } from '@/lib/errorLogger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Custom error page for handling client-side errors in the app
 * This page is shown when an error occurs in any page or component
 */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  React.useEffect(() => {
    // Log the error to Glitchtip when the error page is displayed
    ErrorLogger.logClientError(
      error,
      'ErrorPage',
      undefined, // userId would need to come from context
      typeof window !== 'undefined' ? window.location.pathname : undefined,
      {
        digest: error.digest,
        errorBoundary: 'app-error-page',
      }
    );
  }, [error]);

  const handleRetry = () => {
    // Reset the error boundary and try again
    reset();
  };

  const handleGoHome = () => {
    // Navigate to home page
    window.location.href = '/';
  };

  const errorMessage = process.env.NODE_ENV === 'development' 
    ? error.message || 'An unexpected error occurred'
    : 'An unexpected error occurred. Please try again or return to the home page.';

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-background">
      <Card className="w-full max-w-lg">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3 text-destructive font-serif text-xl sm:text-2xl">
            <AlertTriangle className="h-6 w-6 sm:h-7 sm:w-7 flex-shrink-0" />
            Something went wrong
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
              onClick={handleRetry} 
              className="flex-1"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button 
              onClick={handleGoHome} 
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