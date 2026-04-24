import { Skeleton } from "@/components/ui/skeleton";

export default function ContactLoading() {
  return (
    <div className="flex-1 px-4 py-12 sm:py-16">
        <div className="mx-auto w-full max-w-lg space-y-8">
          {/* Header */}
          <div className="flex flex-col items-center space-y-3">
            <Skeleton className="h-14 w-14 rounded-full" />
            <Skeleton className="h-9 w-48" />
            <Skeleton className="h-5 w-72" />
          </div>

          {/* Form Card */}
          <div className="rounded-2xl border p-6 sm:p-8 space-y-5">
            {/* Name + Email row */}
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-2">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-11 w-full" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-11 w-full" />
              </div>
            </div>

            {/* Phone field */}
            <div className="space-y-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-11 w-full" />
            </div>

            {/* Product interest checkboxes */}
            <div className="space-y-3">
              <Skeleton className="h-4 w-64" />
              <div className="flex gap-5">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-4 rounded" />
                  <Skeleton className="h-4 w-48" />
                </div>
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-4 rounded" />
                  <Skeleton className="h-4 w-44" />
                </div>
              </div>
            </div>

            {/* Message field */}
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-[140px] w-full" />
            </div>

            {/* Submit button */}
            <Skeleton className="h-11 w-full" />
          </div>
        </div>
      </div>
  );
}
