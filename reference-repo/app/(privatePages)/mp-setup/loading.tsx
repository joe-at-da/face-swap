import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function MPSetupLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Skeleton className="h-8 w-48" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="text-center space-y-2 mb-8">
          <Skeleton className="h-10 w-96 mx-auto" />
          <Skeleton className="h-6 w-64 mx-auto" />
        </div>

        <div className="w-full max-w-6xl mx-auto">
          <Card className="w-full max-w-2xl mx-auto">
            <CardHeader className="text-center">
              <Skeleton className="h-8 w-64 mx-auto mb-2" />
              <Skeleton className="h-5 w-48 mx-auto" />
            </CardHeader>
            <CardContent className="space-y-6">
              {/* MP Info Section Skeleton */}
              <div className="border rounded-lg p-6 space-y-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-16 w-16 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-7 w-48" />
                    <Skeleton className="h-5 w-64" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                </div>
              </div>

              {/* Profile Image Skeleton */}
              <div className="flex flex-col items-center space-y-4">
                <Skeleton className="h-24 w-24 rounded-full" />
                <div className="text-center">
                  <Skeleton className="h-4 w-48 mb-1" />
                  <Skeleton className="h-3 w-36" />
                </div>
              </div>

              {/* Form Fields Skeleton */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-10 w-full" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </div>

              {/* MP Following Section Skeleton */}
              <div className="space-y-4">
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-32 w-full rounded-lg" />
              </div>

              {/* Button */}
              <div className="pt-4">
                <Skeleton className="h-12 w-full" />
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

