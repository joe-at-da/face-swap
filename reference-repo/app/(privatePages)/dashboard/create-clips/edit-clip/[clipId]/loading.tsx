import { Skeleton } from "@/components/ui/skeleton";

export default function EditClipLoading() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Desktop layout: horizontal split */}
      <div className="flex h-full">
        {/* Left: Preview + Timeline */}
        <div className="flex flex-col flex-[7] min-w-0">
          {/* Header */}
          <div className="flex-shrink-0 border-b border-border px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
              <Skeleton className="h-7 w-14 rounded-md" />
            </div>
          </div>

          {/* Preview area */}
          <div className="flex-[2] flex items-center justify-center bg-black/90 min-h-0 p-2">
            <Skeleton className="w-full max-w-[640px] aspect-video rounded-sm bg-muted/20" />
          </div>

          {/* Controls bar */}
          <div className="flex-shrink-0 border-t border-border px-3 py-2 space-y-2">
            <Skeleton className="h-2 w-full rounded-full" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
              </div>
              <Skeleton className="h-3 w-24" />
            </div>
          </div>

          {/* Timeline area */}
          <div className="flex-1 min-h-[150px] border-t border-border">
            {/* Timeline toolbar */}
            <div className="flex items-center gap-1 px-2 py-1 border-b border-border">
              <Skeleton className="h-6 w-6 rounded-md" />
              <Skeleton className="h-6 w-6 rounded-md" />
              <div className="w-px h-4 bg-border mx-1" />
              <Skeleton className="h-6 w-6 rounded-md" />
              <Skeleton className="h-6 w-6 rounded-md" />
              <div className="w-px h-4 bg-border mx-1" />
              <Skeleton className="h-6 w-6 rounded-md" />
              <Skeleton className="h-4 w-20 rounded-full" />
              <Skeleton className="h-6 w-6 rounded-md" />
            </div>

            {/* Track rows */}
            <div className="p-2 space-y-1">
              {/* Video track */}
              <div className="flex items-center h-10">
                <Skeleton className="h-8 w-16 rounded-sm mr-2" />
                <Skeleton className="h-8 flex-1 rounded-sm" />
              </div>
              {/* Text track */}
              <div className="flex items-center h-10">
                <Skeleton className="h-8 w-16 rounded-sm mr-2" />
                <Skeleton className="h-8 w-32 rounded-sm" />
              </div>
            </div>
          </div>
        </div>

        {/* Right: Side panel */}
        <div className="flex-[3] border-l border-border min-w-0">
          {/* Tab headers */}
          <div className="flex items-center border-b border-border px-2 py-1 gap-1">
            <Skeleton className="h-7 w-14 rounded-md" />
            <Skeleton className="h-7 w-12 rounded-md" />
            <Skeleton className="h-7 w-16 rounded-md" />
            <Skeleton className="h-7 w-18 rounded-md" />
            <Skeleton className="h-7 w-14 rounded-md" />
          </div>

          {/* Panel content */}
          <div className="p-3 space-y-3">
            <Skeleton className="h-3 w-20" />
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Skeleton className="h-12 w-20 rounded-sm" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2 w-16" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
