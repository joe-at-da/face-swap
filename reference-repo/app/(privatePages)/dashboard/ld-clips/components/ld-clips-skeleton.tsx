import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

export default function LDClipsSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <Skeleton className="h-8 w-40" />

      {/* Search bar */}
      <div className="space-y-3">
        <div className="flex gap-2">
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-28" />
        </div>
        <Skeleton className="h-10 w-full max-w-2xl" />
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Skeleton className="h-10 w-40" />
      </div>

      {/* Result count */}
      <Skeleton className="h-4 w-48" />

      {/* Clips grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-0">
              <Skeleton className="aspect-video w-full rounded-t-lg" />
              <div className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-6 w-6 rounded-full" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-5 w-12 rounded" />
                </div>
                <div className="flex items-center justify-between">
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
