import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Home, Search } from 'lucide-react';
import { GoBackButton } from './components/go-back-button';

/**
 * Custom 404 page for handling page not found errors
 * This page is shown when users navigate to a non-existent route
 */
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-2xl text-center">
        <CardHeader className="pb-6">
          <div className="mx-auto mb-6">
            {/* Large 404 text */}
            <h1 className="text-8xl font-bold text-primary/20 select-none font-serif">
              404
            </h1>
          </div>
          <h2 className="text-2xl sm:text-3xl text-foreground font-serif">
            Page Not Found
          </h2>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <p className="text-lg text-muted-foreground">
              The page you&apos;re looking for doesn&apos;t exist.
            </p>
            <p className="text-sm text-muted-foreground">
              It might have been moved, deleted, or you entered the wrong URL.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
            <Button asChild size="lg">
              <Link href="/">
                <Home className="h-4 w-4 mr-2" />
                Go Home
              </Link>
            </Button>
            
            <GoBackButton />

            <Button variant="outline" size="lg" asChild>
              <Link href="/dashboard">
                <Search className="h-4 w-4 mr-2" />
                Dashboard
              </Link>
            </Button>
          </div>

          {/* Helpful suggestions */}
          <div className="pt-8 border-t border-border">
            <h3 className="text-sm font-semibold text-foreground mb-3">
              Popular Pages:
            </h3>
            <div className="flex flex-wrap gap-2 justify-center">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/">Home</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/dashboard">Dashboard</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/signin">Sign In</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/signup">Sign Up</Link>
              </Button>
            </div>
          </div>

          <div className="text-xs text-muted-foreground pt-4">
            <p>
              If you believe this is an error, please{' '}
              <Link href="/contact" className="text-primary hover:underline">
                contact support
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}