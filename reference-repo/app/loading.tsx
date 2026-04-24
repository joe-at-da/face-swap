import { Card, CardContent } from '@/components/ui/card';

/**
 * Custom loading page shown during page transitions
 * This provides a consistent loading experience across the app
 */
export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center justify-center p-8 space-y-6">
          {/* Loading spinner */}
          <div className="relative">
            <div className="w-12 h-12 border-4 border-muted rounded-full animate-spin border-t-primary"></div>
          </div>

          {/* Loading text */}
          <div className="text-center space-y-2">
            <h2 className="text-lg font-semibold text-foreground">
              Loading...
            </h2>
            <p className="text-sm text-muted-foreground">
              Please wait while we prepare your content
            </p>
          </div>

          {/* Loading dots animation */}
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}