import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function NoTeamAccessLoading() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8">
        <Card className="p-8 md:p-12">
          <div className="space-y-6">
            {/* Icon and Header Skeleton */}
            <div className="text-center space-y-4">
              <div className="flex justify-center">
                <Skeleton className="rounded-full h-20 w-20" />
              </div>

              <div className="space-y-2">
                <Skeleton className="h-10 w-64 mx-auto" />
                <Skeleton className="h-6 w-80 mx-auto" />
              </div>
            </div>

            {/* Alert Skeleton */}
            <Skeleton className="h-32 w-full" />

            {/* What You Can Do Section Skeleton */}
            <div className="space-y-4 pt-4">
              <Skeleton className="h-8 w-48" />

              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            </div>

            {/* Actions Skeleton */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Skeleton className="h-12 flex-1" />
              <Skeleton className="h-12 flex-1" />
            </div>

            {/* Support Contact Skeleton */}
            <div className="text-center pt-4 border-t border-border">
              <Skeleton className="h-4 w-56 mx-auto" />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
