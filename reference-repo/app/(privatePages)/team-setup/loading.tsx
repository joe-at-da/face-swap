import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Logo } from "@/components/logo";

export default function TeamSetupLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Logo  />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="text-center space-y-2 mb-8">
          <Skeleton className="h-10 w-96 mx-auto" />
          <Skeleton className="h-6 w-80 mx-auto" />
        </div>

        <div className="w-full max-w-2xl mx-auto space-y-8">
          <Skeleton className="h-2 w-full" />

          <Card className="p-8">
            <div className="space-y-6">
              <div className="text-center space-y-2">
                <Skeleton className="h-12 w-12 rounded-full mx-auto mb-4" />
                <Skeleton className="h-8 w-64 mx-auto" />
                <Skeleton className="h-4 w-80 mx-auto" />
                <div className="flex items-center justify-center gap-2 mt-3">
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-6 w-32" />
                </div>
              </div>

              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-20 w-20 rounded-lg" />
                    <div>
                      <Skeleton className="h-10 w-32" />
                      <Skeleton className="h-3 w-24 mt-1" />
                    </div>
                  </div>
                </div>

                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}