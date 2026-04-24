import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function TeamSettingsLoading() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <Skeleton className="h-9 w-48 mb-2" />
        <Skeleton className="h-4 w-96" />
      </div>

      {/* Settings Sections */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          {/* Team Information Skeleton */}
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-40 mb-2" />
              <Skeleton className="h-4 w-64" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Skeleton className="h-4 w-20 mb-1" />
                <Skeleton className="h-4 w-32" />
              </div>
              <div>
                <Skeleton className="h-4 w-24 mb-1" />
                <Skeleton className="h-4 w-full" />
              </div>
              <div>
                <Skeleton className="h-4 w-16 mb-1" />
                <Skeleton className="h-4 w-40" />
              </div>
            </CardContent>
          </Card>

          {/* Social Media Posting Settings Skeleton */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <Skeleton className="h-6 w-48 mb-2" />
                  <Skeleton className="h-4 w-64" />
                </div>
                <Skeleton className="h-6 w-24 rounded-full" />
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <Skeleton className="h-16 w-full rounded-lg" />
              <div className="space-y-3">
                <Skeleton className="h-4 w-32" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Team Preferences Skeleton */}
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-40 mb-2" />
              <Skeleton className="h-4 w-56" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-20 w-full rounded-lg" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
