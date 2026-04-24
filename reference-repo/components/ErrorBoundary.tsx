'use client';

import React, { ErrorInfo, ReactNode } from 'react';
import { ErrorLogger } from '@/lib/errorLogger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorId: string | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  componentName?: string;
}

/**
 * Enhanced Error Boundary that integrates with Glitchtip
 * Catches React component errors and provides user-friendly fallback UI
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to Glitchtip
    ErrorLogger.logClientError(
      error,
      this.props.componentName || 'ErrorBoundary',
      undefined, // userId would need to be passed down from a context
      typeof window !== 'undefined' ? window.location.pathname : undefined,
      {
        errorInfo,
        errorId: this.state.errorId,
        componentStack: errorInfo.componentStack,
      }
    );

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Boundary caught an error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    // Reset error state to retry rendering
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
    });
  };

  handleRefresh = () => {
    // Refresh the page
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Error Details</AlertTitle>
                <AlertDescription className="mt-2">
                  {process.env.NODE_ENV === 'development' 
                    ? this.state.error?.message || 'An unexpected error occurred'
                    : 'An unexpected error occurred. Please try again or refresh the page.'
                  }
                </AlertDescription>
              </Alert>

              {this.state.errorId && (
                <div className="text-sm text-muted-foreground">
                  <p>Error ID: <code className="text-xs bg-muted px-1 py-0.5 rounded">{this.state.errorId}</code></p>
                  <p className="mt-1">This error has been automatically reported.</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={this.handleRetry} className="flex-1">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
                <Button onClick={this.handleRefresh} className="flex-1">
                  Refresh Page
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component for wrapping components with error boundary
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps} componentName={Component.displayName || Component.name}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

/**
 * Hook for handling errors in functional components
 */
export function useErrorHandler() {
  const handleError = React.useCallback((error: Error, componentName?: string) => {
    ErrorLogger.logClientError(
      error,
      componentName || 'useErrorHandler',
      undefined, // userId would need to come from context
      typeof window !== 'undefined' ? window.location.pathname : undefined
    );
  }, []);

  return handleError;
}