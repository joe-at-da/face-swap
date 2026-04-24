"use client";

import { useState, useEffect } from "react";
import { ProfileSettingsForm } from "./components/profile-settings-form";
import { NotificationSettings } from "./components/notification-settings";
import { AccountDangerZone } from "./components/account-danger-zone";
import { SocialMediaIntegrationStatus } from "@/app/(privatePages)/mp-setup/components/social-media-integration-status";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { toast } from "sonner";

interface ProfileData {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  created_at: string;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch("/api/settings/profile");
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch profile");
        }

        const profileData = data.data;

        setProfile({
          id: profileData.id,
          email: profileData.email,
          first_name: profileData.first_name,
          last_name: profileData.last_name,
          avatar_url: profileData.avatar_url,
          created_at: profileData.created_at,
        });
      } catch (error) {
        console.error("Error fetching profile:", error);
        setError(error instanceof Error ? error.message : "Failed to load settings");
        toast.error("Failed to load settings");
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const handleProfileUpdate = (updatedProfile: Partial<ProfileData>) => {
    setProfile(prev => prev ? { ...prev, ...updatedProfile } : prev);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-3">
          <h1 className="text-2xl font-bold text-foreground pt-4">Settings</h1>
          <p className="text-lg text-muted-foreground">
            Update your personal and parliamentary information
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
              </CardContent>
            </Card>

            {/* Social Media Integration Skeleton */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Skeleton className="h-6 w-48" />
                  <Skeleton className="h-8 w-8 rounded-full" />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-8 w-20" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {/* Notifications Skeleton */}
            <Card>
              <CardHeader>
                <Skeleton className="h-6 w-40" />
              </CardHeader>
              <CardContent className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-48" />
                    </div>
                    <Skeleton className="h-5 w-10" />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Danger Zone Skeleton */}
            <Card className="border-destructive/20">
              <CardHeader>
                <Skeleton className="h-6 w-24" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
                <Skeleton className="h-10 w-full mt-4" />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="space-y-6">
        <div className="space-y-3">
          <h1 className="text-2xl font-bold text-foreground pt-4">Settings</h1>
          <p className="text-lg text-muted-foreground">
            Update your personal and parliamentary information
          </p>
        </div>

        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center space-y-4">
              <div className="text-destructive">
                <h3 className="text-3xl font-serif font-bold">Settings unavailable</h3>
                <p className="text-sm mt-2">
                  We&apos;re having trouble loading your settings. Please try again or contact support if the problem persists.
                </p>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="text-primary hover:underline text-sm"
              >
                Try again
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h1 className="text-2xl font-bold text-foreground pt-4">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings, preferences, and integrations.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          {/* Profile Settings */}
          <ProfileSettingsForm
            profile={profile}
            onProfileUpdate={handleProfileUpdate}
          />

          {/* Social Media Integration */}
          <SocialMediaIntegrationStatus
            postizCreating={false}
            postizCreated={true}
            postizError={null}
          />
        </div>

        <div className="space-y-6">
          {/* Notification Settings */}
          <NotificationSettings />

          {/* Account Danger Zone */}
          <AccountDangerZone />
        </div>
      </div>
    </div>
  );
}