import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsLoading() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-serif font-bold text-foreground">Settings</h1>
        <p className="text-lg text-muted-foreground">
          Manage your account settings, preferences, and integrations.
        </p>
      </div>
      
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          {/* Profile Settings Skeleton */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-8 w-20" />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <Skeleton className="h-16 w-16 rounded-full" />
                <div className="space-y-2">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-10 w-full" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </div>
              <div className="pt-4 border-t space-y-2">
                <Skeleton className="h-4 w-32" />
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                  <div className="flex justify-between">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-3 w-40" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* MP Following Skeleton */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-8 w-20" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-5 w-12 rounded-full" />
                  </div>
                  <div className="ml-6 space-y-2">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-3 w-3" />
                      <Skeleton className="h-4 w-48" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-3 w-3" />
                      <Skeleton className="h-4 w-36" />
                    </div>
                  </div>
                </div>
                <Skeleton className="h-12 w-full" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Notifications Skeleton */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-5 w-24 rounded-full" />
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Email notifications */}
              <div className="space-y-4">
                <Skeleton className="h-5 w-32" />
                <div className="ml-6 space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-3 w-48" />
                      </div>
                      <Skeleton className="h-5 w-10 rounded-full" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Push notifications */}
              <div className="space-y-4">
                <Skeleton className="h-5 w-36" />
                <div className="ml-6 space-y-3">
                  {Array.from({ length: 2 }).map((_, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Skeleton className="h-4 w-28" />
                        <Skeleton className="h-3 w-40" />
                      </div>
                      <Skeleton className="h-5 w-10 rounded-full" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Coming soon notice */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Skeleton className="h-5 w-5" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-3/4" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone Skeleton */}
          <Card className="border-destructive/20">
            <CardHeader>
              <Skeleton className="h-6 w-24" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}