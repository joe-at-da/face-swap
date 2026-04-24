import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";

export default function CreateTeamLoading() {
  return (
    <div className="container max-w-3xl py-10">
      <Skeleton className="h-4 w-32 mb-8" />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Skeleton className="h-6 w-6 rounded" />
            <Skeleton className="h-8 w-48" />
          </div>
          <Skeleton className="h-4 w-full mt-2" />
          <Skeleton className="h-4 w-3/4" />
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-3 w-64 mt-2" />
          </div>

          <div>
            <Skeleton className="h-4 w-36 mb-2" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-3 w-48 mt-2" />
          </div>

          <div className="flex justify-end gap-3">
            <Skeleton className="h-10 w-20" />
            <Skeleton className="h-10 w-28" />
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 p-6 border rounded-lg">
        <Skeleton className="h-5 w-40 mb-3" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      </div>
    </div>
  );
}