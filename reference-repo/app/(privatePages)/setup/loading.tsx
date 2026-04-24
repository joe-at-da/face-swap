import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default function SetupPageLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 md:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center space-x-2">
                <h1 className="font-serif text-xl md:text-2xl font-bold text-foreground">
                  Parliament Connect
                </h1>
                <Badge variant="secondary" className="text-xs">Setup</Badge>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-8">
        <div className="text-center space-y-2 mb-8">
          <Skeleton className="h-10 w-80 mx-auto" />
          <Skeleton className="h-6 w-60 mx-auto" />
        </div>

        <div className="w-full max-w-6xl mx-auto space-y-8">
          {/* Progress Skeleton */}
          <div className="w-full max-w-4xl mx-auto px-4 py-6">
            <div className="flex items-center justify-center">
              {[1, 2, 3].map((step, index) => (
                <div key={step} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <Skeleton className="w-10 h-10 rounded-full" />
                    <div className="mt-2 text-center">
                      <Skeleton className="h-4 w-16 mb-1" />
                      <Skeleton className="h-3 w-20 hidden sm:block" />
                    </div>
                  </div>
                  {index < 2 && (
                    <Skeleton className="h-0.5 mx-4 w-12 sm:w-20 md:w-32" />
                  )}
                </div>
              ))}
            </div>
            
            <div className="mt-6">
              <div className="flex justify-between text-sm mb-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-24" />
              </div>
              <Skeleton className="w-full h-2 rounded-full" />
            </div>
          </div>

          {/* Form Skeleton */}
          <div className="flex justify-center">
            <Card className="w-full max-w-2xl mx-auto">
              <CardHeader className="text-center">
                <Skeleton className="h-8 w-64 mx-auto mb-2" />
                <Skeleton className="h-5 w-48 mx-auto" />
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Profile Image */}
                <div className="flex flex-col items-center space-y-4">
                  <Skeleton className="h-24 w-24 rounded-full" />
                  <div className="text-center">
                    <Skeleton className="h-4 w-48 mb-1" />
                    <Skeleton className="h-3 w-36" />
                  </div>
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>

                {/* Button */}
                <div className="pt-4">
                  <Skeleton className="h-12 w-full" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}