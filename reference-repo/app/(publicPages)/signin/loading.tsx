import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function SignInLoading() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Back to Home Link Skeleton */}
      <div className="p-4 md:p-6">
        <Skeleton className="h-5 w-32" />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Logo/Title Skeleton */}
          <div className="text-center space-y-2">
            <Skeleton className="h-10 w-64 mx-auto" />
            <Skeleton className="h-6 w-80 mx-auto" />
          </div>

          {/* Sign In Card Skeleton */}
          <Card className="border-border/50 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <Skeleton className="h-7 w-48" />
              <Skeleton className="h-5 w-full" />
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Form fields */}
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              
              {/* Submit button */}
              <Skeleton className="h-11 w-full mt-4" />
            </CardContent>
          </Card>

          {/* Parliament Member Badge Skeleton */}
          <div className="text-center space-y-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <Skeleton className="h-4 w-32 bg-background" />
              </div>
            </div>
            <Skeleton className="h-8 w-64 mx-auto rounded-full" />
          </div>

          {/* Sign Up Link Skeleton */}
          <div className="text-center">
            <Skeleton className="h-5 w-56 mx-auto" />
          </div>
        </div>
      </div>
    </div>
  );
}

