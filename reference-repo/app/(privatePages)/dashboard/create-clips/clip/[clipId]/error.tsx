'use client';

import { useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react';
import Link from 'next/link';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ClipDetailError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log error to monitoring service
    console.error('Clip detail page error:', error);
  }, [error]);

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <div className="space-y-6">
        {/* Back button */}
        <Button variant="ghost" asChild className="gap-2">
          <Link href="/dashboard/create-clips">
            <ArrowLeft className="h-4 w-4" />
            Back to Clips
          </Link>
        </Button>

        {/* Error content */}
        <Card>
          <CardContent className="p-12 text-center space-y-6">
            <div className="mx-auto w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
              <AlertTriangle className="h-8 w-8 text-destructive" />
            </div>
            
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold">Something went wrong</h1>
              <p className="text-muted-foreground">
                We encountered an error while loading this clip. This might be due to:
              </p>
              <ul className="text-sm text-muted-foreground text-left max-w-md mx-auto space-y-1">
                <li>• The clip might not exist or has been removed</li>
                <li>• There might be a temporary server issue</li>
                <li>• Your internet connection might be unstable</li>
              </ul>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={reset} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Try Again
              </Button>
              <Button variant="outline" asChild>
                <Link href="/dashboard/create-clips">
                  Go Back to Clips
                </Link>
              </Button>
            </div>

            {error.digest && (
              <p className="text-xs text-muted-foreground mt-4">
                Error ID: {error.digest}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}