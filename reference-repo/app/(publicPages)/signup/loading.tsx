import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function SignUpLoading() {
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
            <Skeleton className="h-10 w-72 mx-auto" />
            <Skeleton className="h-6 w-80 mx-auto" />
          </div>

          {/* Sign Up Card Skeleton */}
          <Card className="border-border/50 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <Skeleton className="h-7 w-52" />
              <Skeleton className="h-5 w-full" />
            </CardHeader>
            <CardContent className="space-y-4">
              {/* MP Verification Info Skeleton */}
              <Skeleton className="h-24 w-full rounded-lg" />
              
              {/* Form fields */}
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              
              {/* Submit button */}
              <Skeleton className="h-11 w-full mt-4" />
            </CardContent>
          </Card>

          {/* Features List Skeleton */}
          <div className="space-y-3">
            <Skeleton className="h-5 w-40 mx-auto" />
            <div className="grid grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

