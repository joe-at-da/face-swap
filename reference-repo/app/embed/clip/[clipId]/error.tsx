'use client';

import React from 'react';
import { ErrorLogger } from '@/lib/errorLogger';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function EmbedClipError({ error, reset }: ErrorPageProps) {
  React.useEffect(() => {
    ErrorLogger.logClientError(
      error,
      'EmbedClipError',
      undefined,
      typeof window !== 'undefined' ? window.location.pathname : undefined,
      {
        digest: error.digest,
        errorBoundary: 'embed-clip-error-page',
      }
    );
  }, [error]);

  return (
    <div className="relative w-full h-screen flex flex-col items-center justify-center bg-black text-white">
      <div className="text-center space-y-4 px-4">
        <AlertTriangle className="h-12 w-12 text-destructive mx-auto" />
        <h1 className="text-xl font-semibold">Error Loading Video</h1>
        <p className="text-sm text-muted-foreground max-w-md">
          We encountered an error while loading this video clip.
        </p>
        {error.digest && (
          <p className="text-xs text-muted-foreground">
            Error ID: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-2 mx-auto"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
      </div>
    </div>
  );
}

