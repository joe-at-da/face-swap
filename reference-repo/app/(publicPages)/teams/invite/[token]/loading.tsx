import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-40">
      <div className="w-full max-w-[620px] bg-card border border-border rounded-xl p-8 space-y-10 shadow-sm">
        {/* Header Section Skeleton */}
        <div className="flex flex-col items-center gap-2 text-center">
          <Skeleton className="w-16 h-16 rounded-full" />
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-7 w-96 max-w-full" />
        </div>

        {/* Team Name Section Skeleton */}
        <div className="flex flex-col items-center gap-5">
          <Skeleton className="h-7 w-48" />

          {/* Team Owner Card Skeleton */}
          <div className="flex items-center justify-between w-full gap-5">
            <div className="flex items-center gap-4 flex-1">
              <Skeleton className="w-12 h-12 rounded-full flex-shrink-0" />
              <div className="flex flex-col gap-2 flex-1">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-6 w-48 max-w-full" />
              </div>
            </div>
            <Skeleton className="h-7 w-28 rounded-full flex-shrink-0" />
          </div>
        </div>

        {/* Invitation Details Skeleton */}
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between py-2.5 border-b border-border gap-4">
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-7 w-48" />
          </div>
          <div className="flex items-center justify-between py-2.5 border-b border-border gap-4">
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-7 w-32" />
          </div>
          <div className="flex items-center justify-between py-2.5 border-b border-border gap-4">
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-7 w-28" />
          </div>
        </div>

        {/* Benefits Card Skeleton */}
        <div className="flex items-start gap-5 p-4 bg-muted rounded-md border border-border">
          <Skeleton className="w-12 h-12 rounded-lg flex-shrink-0" />
          <div className="flex flex-col gap-2 flex-1">
            <Skeleton className="h-6 w-64 max-w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>

        {/* Action Buttons Skeleton */}
        <div className="flex flex-col items-center gap-6">
          <Skeleton className="w-full h-12 rounded-md" />
          <Skeleton className="w-48 h-12 rounded-md" />
        </div>
      </div>
    </div>
  );
}
