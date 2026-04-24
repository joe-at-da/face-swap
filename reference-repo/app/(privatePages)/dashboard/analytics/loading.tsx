import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardAnalyticsLoading() {
  return (
    <div className="space-y-6 pt-4">
      <div className="space-y-2">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-5 w-96 max-w-full" />
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(0,280px)_auto]">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-[260px]" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={index}>
            <CardHeader className="space-y-3">
              <Skeleton className="h-5 w-28" />
              <Skeleton className="h-10 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[170px] w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
