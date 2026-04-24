import { Skeleton } from "@/components/ui/skeleton";

export default function HomePageLoading() {
  return (
    <div className="min-h-screen">
      {/* Hero Section Skeleton */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="flex lg:flex-row flex-col justify-center items-center lg:gap-10">
            <div className="lg:w-1/2 w-full mb-10 lg:mb-0 space-y-6">
              {/* Hero Heading */}
              <div className="space-y-4">
                <Skeleton className="h-16 w-full max-w-2xl" />
                <Skeleton className="h-8 w-full max-w-xl" />
                <Skeleton className="h-8 w-full max-w-lg" />
              </div>
              
              {/* List items */}
              <div className="space-y-3">
                <Skeleton className="h-6 w-full max-w-md" />
                <Skeleton className="h-6 w-full max-w-md" />
                <Skeleton className="h-6 w-full max-w-md" />
                <Skeleton className="h-6 w-full max-w-md" />
              </div>
              
              {/* CTA Button */}
              <Skeleton className="h-12 w-48" />
            </div>
            <div className="lg:w-1/2 lg:block hidden">
              <Skeleton className="aspect-video w-full rounded-lg" />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section Skeleton */}
      <section className="py-16 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <Skeleton className="h-10 w-64 mx-auto mb-4" />
            <Skeleton className="h-6 w-96 mx-auto" />
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-4">
                <Skeleton className="h-12 w-12 rounded-lg" />
                <Skeleton className="h-7 w-32" />
                <Skeleton className="h-20 w-full" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow Section Skeleton */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <Skeleton className="h-10 w-72 mx-auto mb-4" />
            <Skeleton className="h-6 w-96 mx-auto" />
          </div>
          <div className="space-y-8 max-w-4xl mx-auto">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-start gap-4">
                <Skeleton className="h-12 w-12 rounded-full flex-shrink-0" />
                <div className="flex-1 space-y-3">
                  <Skeleton className="h-6 w-48" />
                  <Skeleton className="h-20 w-full" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section Skeleton */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-6 max-w-2xl mx-auto">
            <Skeleton className="h-12 w-full max-w-xl mx-auto" />
            <Skeleton className="h-6 w-full max-w-lg mx-auto" />
            <Skeleton className="h-12 w-48 mx-auto" />
          </div>
        </div>
      </section>
    </div>
  );
}

