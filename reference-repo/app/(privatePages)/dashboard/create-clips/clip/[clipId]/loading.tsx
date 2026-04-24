import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ClipDetailLoading() {
  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Back button skeleton */}
      <Skeleton className="h-10 w-24" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video player section */}
        <div className="lg:col-span-2 space-y-4">
          {/* Video player skeleton */}
          <Card>
            <CardContent className="p-6">
              <Skeleton className="w-full aspect-video rounded-lg" />
              
              {/* Video controls skeleton */}
              <div className="mt-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <Skeleton className="h-10 w-10 rounded-full" />
                </div>
                <Skeleton className="h-4 w-20" />
              </div>
            </CardContent>
          </Card>

          {/* Tabs skeleton */}
          <Card>
            <CardHeader>
              <div className="flex space-x-2">
                <Skeleton className="h-10 w-24" />
                <Skeleton className="h-10 w-20" />
              </div>
            </CardHeader>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* MP Info skeleton */}
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Skeleton className="h-12 w-12 rounded-full" />
                <div className="space-y-2">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-5 w-16" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Clip Details skeleton */}
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-28" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              </div>
              
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-28" />
              </div>
            </CardContent>
          </Card>

          {/* Actions skeleton */}
          <Card>
            <CardContent className="p-6">
              <div className="space-y-3">
                <Skeleton className="h-11 w-full" />
                <div className="flex gap-2">
                  <Skeleton className="h-11 flex-1" />
                  <Skeleton className="h-11 flex-1" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Transcript skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-24" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </CardContent>
      </Card>
    </div>
  );
}