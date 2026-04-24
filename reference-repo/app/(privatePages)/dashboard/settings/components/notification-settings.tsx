"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export function NotificationSettings() {
  const [newClipsAvailable, setNewClipsAvailable] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch("/api/settings/notifications");
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch notification settings");
        }

        setNewClipsAvailable(data.data.new_clips_available);
      } catch (error) {
        console.error("Error fetching notification settings:", error);
        setFetchError(true);
        toast.error("Failed to load notification settings");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleToggle = async (checked: boolean) => {
    const previousValue = newClipsAvailable;
    setNewClipsAvailable(checked);
    setIsUpdating(true);

    try {
      const response = await fetch("/api/settings/notifications", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_clips_available: checked }),
      });

      if (!response.ok) {
        throw new Error("Failed to update notification settings");
      }

      toast.success("Notification settings updated");
    } catch {
      setNewClipsAvailable(previousValue);
      toast.error("Failed to update notification settings");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold font-sans">
          Notification Preferences
        </CardTitle>
        <p className="text-base text-muted-foreground mt-1">
          Choose what notifications you&apos;d like to receive
        </p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
            </div>
            <Skeleton className="h-5 w-10" />
          </div>
        ) : fetchError ? (
          <p className="text-sm text-destructive">
            Unable to load notification settings. Please refresh the page.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label
                htmlFor="new-clips-available"
                className="text-base text-primary font-sans font-normal"
              >
                New clips available
              </Label>
              <p className="text-sm text-muted-foreground">
                When your followed MP speaks in Parliament
              </p>
            </div>
            <Switch
              id="new-clips-available"
              checked={newClipsAvailable}
              onCheckedChange={handleToggle}
              disabled={isUpdating}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
