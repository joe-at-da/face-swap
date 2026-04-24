import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function PortraitCollectionLoading() {
  return (
    <div className="container mx-auto max-w-5xl py-8">
      <div className="mb-8 space-y-2">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-5 w-96" />
      </div>

      <div className="space-y-6">
        {/* Progress Card Skeleton */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <Skeleton className="h-2 w-full" />
              </div>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-8 w-16" />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Card Skeleton */}
        <Card>
          <CardHeader>
            <Skeleton className="h-7 w-48" />
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Video Skeleton */}
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="aspect-video w-full rounded-lg" />
            </div>

            {/* Transcript Skeleton */}
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <div className="space-y-2 rounded-lg border border-border p-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </div>

            {/* Faces Grid Skeleton */}
            <div className="space-y-3">
              <Skeleton className="h-4 w-48" />
              <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="aspect-square rounded-lg" />
                ))}
              </div>
            </div>

            {/* Candidates Skeleton */}
            <div className="space-y-3">
              <Skeleton className="h-4 w-48" />
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-24 w-full rounded-lg" />
                ))}
              </div>
            </div>

            {/* Button Skeleton */}
            <Skeleton className="h-12 w-full rounded-lg" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
