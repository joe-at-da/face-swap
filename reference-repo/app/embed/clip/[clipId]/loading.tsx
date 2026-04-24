import { Skeleton } from "@/components/ui/skeleton";

export default function EmbedClipLoading() {
  return (
    <div className="relative w-full h-screen flex flex-col bg-black">
      {/* Video Player Skeleton */}
      <div className="flex-1 flex items-center justify-center">
        <Skeleton className="aspect-video w-full max-w-7xl mx-auto bg-muted" />
      </div>

      {/* Watermark Area Skeleton */}
      <div className="absolute bottom-4 left-4">
        <Skeleton className="h-8 w-48 bg-black/70" />
      </div>
    </div>
  );
}

