import { Skeleton } from "@/components/ui/skeleton";

export default function TeamClipsLoading() {
  return (
    <div className="space-y-8">
      {/* Header skeleton */}
      <div className="space-y-2">
        <Skeleton className="h-11 w-64" />
        <Skeleton className="h-7 w-96" />
      </div>

      {/* Search and filters skeleton */}
      <div className="space-y-4">
        <div className="border rounded-lg p-6">
          <Skeleton className="h-11 w-full max-w-2xl" />
          <div className="flex gap-2 mt-4">
            <Skeleton className="h-11 w-32" />
            <Skeleton className="h-11 w-40" />
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="flex gap-4">
            <Skeleton className="h-11 w-48" />
            <Skeleton className="h-11 w-28" />
            <Skeleton className="h-11 w-32" />
          </div>
        </div>
      </div>

      {/* Results summary skeleton */}
      <Skeleton className="h-5 w-48" />

      {/* Grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="space-y-4 border rounded-lg overflow-hidden">
            <Skeleton className="aspect-video w-full" />
            <div className="p-4 space-y-3">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <div className="flex justify-between items-center pt-2 border-t">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-5 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
