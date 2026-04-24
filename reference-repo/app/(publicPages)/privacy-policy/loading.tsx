import { Skeleton } from "@/components/ui/skeleton";

export default function PrivacyPolicyLoading() {
  return (
    <div className="flex-1 px-4 py-12 sm:py-16">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <div className="flex flex-col items-center space-y-3">
          <Skeleton className="h-14 w-14 rounded-full" />
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-5 w-80" />
        </div>

        <div className="space-y-6">
          <Skeleton className="h-8 w-3/4" />
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
          <Skeleton className="h-7 w-1/2" />
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <Skeleton className="h-7 w-2/3" />
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </div>
      </div>
    </div>
  );
}
